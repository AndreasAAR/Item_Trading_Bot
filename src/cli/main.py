import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.storage.database import get_db
from src.tradera.client import TraderaClient
from src.storage.repository import SyncRepository
from src.blocket.session import BlocketSessionManager
from src.blocket.drafter import BlocketDrafter
from src.facebook.session import FacebookSessionManager
from src.facebook.drafter import FacebookDrafter

console = Console()

def cmd_fetch(args=None):
    """Fetch active listings from Tradera and sync with local database."""
    console.print(Panel("[bold green]Fetching active items from Tradera (ODENPLAN SALES)...[/bold green]"))
    client = TraderaClient()
    repo = SyncRepository()

    cards = client.get_profile_items()
    console.print(f"Found [bold cyan]{len(cards)}[/bold cyan] active listings on profile.")

    new_count = 0
    updated_count = 0
    relisted_count = 0

    for idx, card in enumerate(cards, 1):
        try:
            detail = client.get_item_detail(card.url, delay_seconds=0.2)
            if detail.buy_now_price is None and card.buy_now_price is not None:
                detail.buy_now_price = card.buy_now_price
            if detail.starting_price is None and card.starting_price is not None:
                detail.starting_price = card.starting_price

            outcome, matched_item, reason = repo.upsert_item_detailed(detail)
            if outcome == "new":
                new_count += 1
            elif outcome == "relisted":
                relisted_count += 1
                old_id = matched_item["item_id"]
                console.print(
                    f"  [cyan]-> Relisted item recognized:[/cyan] '{detail.title}' "
                    f"(ID #{old_id} -> #{detail.item_id}) [{reason}] - Preserved sync states."
                )
            else:
                updated_count += 1
        except Exception as e:
            console.print(f"[red]Error fetching {card.url}: {e}[/red]")

    console.print(
        f"• Discovered: [bold green]{new_count}[/bold green] new, "
        f"[bold]{updated_count}[/bold] refreshed, "
        f"[bold cyan]{relisted_count}[/bold cyan] relisted (deduplicated)."
    )
    return new_count, updated_count, relisted_count

def cmd_list(args):
    """List tracked items and their sync status."""
    repo = SyncRepository()
    items = repo.list_items()

    if not items:
        console.print("[yellow]No items found in local database. Run 'python -m src.cli fetch' first.[/yellow]")
        return

    table = Table(title=f"Tradera Multi-Platform Sync Status ({len(items)} items)")
    table.add_column("Item ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white", max_width=35)
    table.add_column("Buy Now", style="green", justify="right")
    table.add_column("Target Price", style="bold yellow", justify="right")
    table.add_column("Images", justify="center")
    table.add_column("Blocket", style="magenta")
    table.add_column("Facebook", style="blue")

    for item in items:
        bn = f"{item['buy_now_price']} kr" if item.get('buy_now_price') else "-"
        target = f"{item['target_price']} kr"
        img_count = str(len(item.get('images', [])))
        b_status = item.get('status', 'discovered')
        fb_status = item.get('facebook_status', 'discovered')

        b_color = "green" if b_status == "published" else ("cyan" if b_status == "drafted" else "white")
        fb_color = "green" if fb_status == "published" else ("cyan" if fb_status == "drafted" else "white")

        table.add_row(
            item['item_id'],
            item['title'],
            bn,
            target,
            img_count,
            f"[{b_color}]{b_status}[/{b_color}]",
            f"[{fb_color}]{fb_status}[/{fb_color}]"
        )

    console.print(table)

def cmd_login(args=None):
    """Interactive login to Blocket to save session state."""
    session_mgr = BlocketSessionManager()
    session_mgr.interactive_login(email=getattr(args, "email", None))

def cmd_fb_login(args=None):
    """Interactive login to Facebook Marketplace to save session state."""
    fb_mgr = FacebookSessionManager()
    if getattr(args, "c_user", None) and getattr(args, "xs", None):
        fb_mgr.save_manual_cookies(args.c_user, args.xs)
    elif getattr(args, "cookies", None):
        fb_mgr.save_cookie_string(args.cookies)
    elif getattr(args, "import_chrome", False):
        fb_mgr.import_chrome_cookies()
    elif getattr(args, "cdp", False):
        fb_mgr.login_via_cdp()
    else:
        fb_mgr.interactive_login()

def cmd_draft(args):
    """Draft item(s) to Blocket."""
    repo = SyncRepository()
    session_mgr = BlocketSessionManager()

    if not session_mgr.has_saved_session():
        console.print("[yellow]Warning: No saved Blocket session found.[/yellow]")
        console.print("Run '[bold]python -m src.cli login[/bold]' first to log in with your account.")
        return

    drafter = BlocketDrafter(session_mgr)

    if args.item_id:
        item = repo.get_item(args.item_id)
        if not item:
            console.print(f"[red]Item {args.item_id} not found in database.[/red]")
            return
        items_to_draft = [item]
    elif args.all or args.limit:
        items_to_draft = repo.list_items(status="discovered", platform="blocket")
        if args.limit:
            items_to_draft = items_to_draft[:args.limit]
        console.print(f"Found [bold cyan]{len(items_to_draft)}[/bold cyan] discovered items to draft.")
    else:
        console.print("[red]Please specify either --item-id <ID>, --all, or --limit <N>.[/red]")
        return

    delay = getattr(args, "delay", 10.0)
    publish_mode = getattr(args, "publish", False)

    def on_success(item_id, url, status="drafted"):
        repo.update_status(item_id, status, blocket_ad_url=url)

    drafter.draft_batch(
        items_to_draft,
        headless=getattr(args, "headless", False),
        delay_between=delay,
        publish=publish_mode,
        on_success=on_success
    )

def cmd_publish(args):
    """Directly publish listing(s) to Blocket."""
    repo = SyncRepository()
    session_mgr = BlocketSessionManager()

    if not session_mgr.has_saved_session():
        console.print("[yellow]Warning: No saved Blocket session found.[/yellow]")
        console.print("Run '[bold]python -m src.cli login[/bold]' first to log in with your account.")
        return

    drafter = BlocketDrafter(session_mgr)

    if args.item_id:
        item = repo.get_item(args.item_id)
        if not item:
            console.print(f"[red]Item {args.item_id} not found in database.[/red]")
            return
        items_to_publish = [item]
    elif args.all or args.limit:
        items_to_publish = repo.list_items(status="discovered", platform="blocket")
        if args.limit:
            items_to_publish = items_to_publish[:args.limit]
        console.print(f"Found [bold cyan]{len(items_to_publish)}[/bold cyan] discovered items to publish.")
    else:
        console.print("[red]Please specify either --item-id <ID>, --all, or --limit <N>.[/red]")
        return

    delay = getattr(args, "delay", 30.0)

    def on_success(item_id, url, status="published"):
        repo.update_status(item_id, status, blocket_ad_url=url)

    drafter.draft_batch(
        items_to_publish,
        headless=getattr(args, "headless", False),
        delay_between=delay,
        publish=True,
        on_success=on_success
    )

def cmd_fb_draft(args):
    """Draft item(s) to Facebook Marketplace."""
    repo = SyncRepository()
    fb_mgr = FacebookSessionManager()

    if not fb_mgr.has_saved_session():
        console.print("[yellow]Warning: No saved Facebook session found.[/yellow]")
        console.print("Run '[bold]python -m src.cli fb-login[/bold]' first to log in with your account.")
        return

    drafter = FacebookDrafter(fb_mgr)

    if args.item_id:
        item = repo.get_item(args.item_id)
        if not item:
            console.print(f"[red]Item {args.item_id} not found in database.[/red]")
            return
        items_to_draft = [item]
    elif args.all or args.limit:
        items_to_draft = repo.list_items(status="discovered", platform="facebook")
        if args.limit:
            items_to_draft = items_to_draft[:args.limit]
        console.print(f"Found [bold cyan]{len(items_to_draft)}[/bold cyan] discovered items to draft on Facebook.")
    else:
        console.print("[red]Please specify either --item-id <ID>, --all, or --limit <N>.[/red]")
        return

    delay = getattr(args, "delay", 15.0)
    publish_mode = getattr(args, "publish", False)

    def on_success(item_id, url, status="drafted"):
        repo.update_facebook_status(item_id, status, facebook_ad_url=url)

    if len(items_to_draft) == 1 and getattr(args, "review", False):
        drafter.draft_item(items_to_draft[0], publish=publish_mode, pause_for_user=True)
        on_success(items_to_draft[0]["item_id"], "https://www.facebook.com/marketplace", status="published" if publish_mode else "drafted")
    else:
        drafter.draft_batch(
            items_to_draft,
            headless=getattr(args, "headless", False),
            delay_between=delay,
            publish=publish_mode,
            on_success=on_success
        )

def cmd_sync(args):
    """One-command pipelined workflow: Fetch Tradera items -> Batch-draft unsynced items to Blocket and/or Facebook."""
    target = getattr(args, "target", "blocket").lower()
    console.print(Panel(f"[bold green]Running One-Click Pipeline: Tradera -> {target.upper()} Sync[/bold green]"))
    repo = SyncRepository()

    # 1. Fetch fresh items from Tradera
    cmd_fetch()

    # 1.5. Reconcile sold items on Tradera -> unlist from Blocket (Aktiva & Utkast) & Facebook
    console.print("\n[bold cyan]Checking for sold items on Tradera to unlist...[/bold cyan]")
    cmd_sync_sold(argparse.Namespace(dry_run=False, headless=getattr(args, "headless", True)))

    # 2. Sync to Blocket if requested
    if target in ["blocket", "all"]:
        session_mgr = BlocketSessionManager()
        if not session_mgr.has_saved_session():
            console.print("[yellow]No Blocket session found. Opening one-time login...[/yellow]")
            cmd_login()

        unsynced_blocket = repo.list_items(status="discovered", platform="blocket")
        if getattr(args, "limit", None):
            unsynced_blocket = unsynced_blocket[:args.limit]

        if unsynced_blocket:
            console.print(f"\n[bold cyan]Drafting {len(unsynced_blocket)} items to Blocket cloud drafts...[/bold cyan]")
            drafter = BlocketDrafter(session_mgr)
            drafter.draft_batch(
                unsynced_blocket,
                headless=getattr(args, "headless", False),
                delay_between=1.5,
                on_success=lambda i_id, url, status="drafted": repo.update_status(i_id, status, blocket_ad_url=url)
            )
        else:
            console.print("[bold green]All items are already synchronized to Blocket drafts![/bold green]")

    # 3. Sync to Facebook if requested
    if target in ["facebook", "all"]:
        fb_mgr = FacebookSessionManager()
        if not fb_mgr.has_saved_session():
            console.print("[yellow]No Facebook session found. Opening one-time login...[/yellow]")
            cmd_fb_login()

        unsynced_fb = repo.list_items(status="discovered", platform="facebook")
        if getattr(args, "limit", None):
            unsynced_fb = unsynced_fb[:args.limit]

        if unsynced_fb:
            console.print(f"\n[bold cyan]Publishing {len(unsynced_fb)} new items to Facebook Marketplace...[/bold cyan]")
            fb_drafter = FacebookDrafter(fb_mgr)
            fb_drafter.draft_batch(
                unsynced_fb,
                headless=getattr(args, "headless", False),
                delay_between=15.0,
                publish=True,
                on_success=lambda i_id, url, status="published": repo.update_facebook_status(i_id, status, facebook_ad_url=url)
            )
        else:
            console.print("[bold green]All items are already synchronized to Facebook Marketplace![/bold green]")

    console.print(Panel(
        f"[bold green]Pipeline Complete![/bold green]\n"
        f"• All targeted items processed for [bold cyan]{target.upper()}[/bold cyan]."
    ))

def cmd_set_price(args):
    """Manually update the target price for an item."""
    repo = SyncRepository()
    item = repo.get_item(args.item_id)
    if not item:
        console.print(f"[red]Item {args.item_id} not found.[/red]")
        return
    repo.update_price(args.item_id, args.price)
    console.print(f"[green]Updated item {args.item_id} price to {args.price} kr.[/green]")

def cmd_set_floor(args):
    """Set custom floor price for an item."""
    from src.pricing.ladder import round_to_nine
    repo = SyncRepository()
    item = repo.get_item(args.item_id)
    if not item:
        console.print(f"[red]Item {args.item_id} not found.[/red]")
        return
    floor = round_to_nine(args.floor)
    success = repo.set_floor_price(args.item_id, floor)
    if success:
        console.print(f"[bold green][OK] Floor price for #{args.item_id} set to {floor} kr.[/bold green]")
    else:
        console.print(f"[red]Failed to update floor price for #{args.item_id}.[/red]")

def cmd_ladder(args):
    """View items and their 5-phase pricing ladder stages and image rotation status."""
    repo = SyncRepository()
    items = repo.list_ladder_items()
    if not items:
        console.print("[yellow]No items found in database.[/yellow]")
        return

    table = Table(title=f"Pricing Ladder & Visual Rotation ({len(items)} items)")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white", max_width=30)
    table.add_column("Base", justify="right", style="white")
    table.add_column("Floor", justify="right", style="dim red")
    table.add_column("Step", justify="center")
    table.add_column("Current Price", justify="right", style="bold yellow")
    table.add_column("Next Transition", style="magenta")
    table.add_column("Img #", justify="center", style="blue")
    table.add_column("Relists", justify="center", style="dim")

    for it in items:
        step = it.get("ladder_step", 0)
        curr_price = it.get("target_price", 0)
        base = it.get("base_price", 0)
        floor = it.get("floor_price", 0)
        next_p = it.get("next_price", 0)
        next_drop = it.get("next_is_drop", False)

        step_str = f"S{step}: {it.get('stage_name', '')}"
        if it.get("is_drop_event"):
            step_str = f"[bold green]{step_str}*[/bold green]"

        next_str = f"S{it.get('next_step')}: {next_p} kr"
        if next_drop:
            next_str += " [bold green](DROP!)[/bold green]"

        table.add_row(
            str(it["item_id"]),
            it["title"][:30],
            f"{base} kr",
            f"{floor} kr",
            step_str,
            f"{curr_price} kr",
            next_str,
            f"#{it.get('cover_image_index', 0)}",
            str(it.get("relist_count", 0))
        )

    console.print(table)
    console.print("[dim]* = Price drop alert triggered on platform during this stage[/dim]")

def cmd_advance_ladder(args):
    """Manually advance item(s) to the next ladder step and rotate cover image."""
    repo = SyncRepository()
    if getattr(args, "item_id", None):
        res = repo.advance_item_ladder(args.item_id)
        if not res:
            console.print(f"[red]Item {args.item_id} not found.[/red]")
            return
        drop_tag = " [bold green](PRICE DROP ALERT!)[/bold green]" if res["is_drop_event"] else ""
        console.print(
            f"[bold green][OK] Advanced Item #{args.item_id}:[/bold green]\n"
            f"  • New Stage: [bold yellow]Step {res['ladder_step']} ({res['stage_desc']})[/bold yellow]{drop_tag}\n"
            f"  • New Price: [bold yellow]{res['target_price']} kr[/bold yellow] (Floor: {res['floor_price']} kr)\n"
            f"  • Cover Image Index: [cyan]#{res['cover_image_index']}[/cyan] (Relist Count: {res['relist_count']})"
        )
    elif getattr(args, "all", False):
        items = repo.list_items()
        count = 0
        for it in items:
            repo.advance_item_ladder(it["item_id"])
            count += 1
        console.print(f"[bold green][OK] Advanced all {count} items to their next ladder stage and cover image.[/bold green]")
    else:
        console.print("[red]Please specify --item-id <ID> or --all.[/red]")

def cmd_clean_drafts(args):
    """Delete all drafts from Blocket cloud account and reset local item statuses."""
    from src.blocket.cleaner import BlocketDraftCleaner
    console.print(Panel("[bold yellow]Cleaning all drafts from Blocket account...[/bold yellow]"))
    cleaner = BlocketDraftCleaner()
    count = cleaner.clean_all_drafts(headless=getattr(args, "headless", True))
    
    # Reset local database statuses to discovered
    repo = SyncRepository()
    with get_db(repo.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE items SET status = 'discovered', blocket_ad_id = NULL, blocket_ad_url = NULL WHERE status = 'drafted'")
def cmd_dedupe(args):
    """Scan database for duplicate listings and optionally merge them."""
    console.print(Panel("[bold green]Scanning database for duplicate or relisted items...[/bold green]"))
    repo = SyncRepository()
    duplicates = repo.find_all_duplicates()

    if not duplicates:
        console.print("[bold green][OK] No duplicate items found in database! Inventory is clean.[/bold green]")
        return

    console.print(f"Found [bold yellow]{len(duplicates)}[/bold yellow] duplicate cluster(s):")
    for cluster in duplicates:
        p = cluster["primary_item"]
        console.print(f"\n[bold white]Primary Item #{p['item_id']}:[/bold white] {p['title']}")
        console.print(f"  Target Price: {p.get('target_price')} SEK | Blocket: [{p.get('status')}], Facebook: [{p.get('facebook_status')}]")
        for dup in cluster["duplicate_items"]:
            d = dup["item"]
            reason = dup["reason"]
            console.print(f"  [yellow]-> Duplicate #{d['item_id']}:[/yellow] {d['title']} ({reason})")
            console.print(f"    Target Price: {d.get('target_price')} SEK | Blocket: [{d.get('status')}], Facebook: [{d.get('facebook_status')}]")

            if getattr(args, "merge", False):
                success = repo.merge_duplicate_items(p["item_id"], d["item_id"])
                if success:
                    console.print(f"    [bold green][OK] Merged duplicate #{d['item_id']} into #{p['item_id']}[/bold green]")
                else:
                    console.print(f"    [bold red][FAIL] Failed to merge #{d['item_id']}[/bold red]")

def cmd_tradera_login(args=None):
    """Log in to Tradera and save session state for unlisting."""
    from src.tradera.session import TraderaSessionManager
    mgr = TraderaSessionManager()
    if getattr(args, "cookies", None):
        mgr.save_cookie_string(args.cookies)
    elif getattr(args, "trd_at", None):
        mgr.save_manual_cookies(args.trd_at, getattr(args, "trd_rt", ""))
    else:
        mgr.interactive_login()

def cmd_sync_sold(args):
    """Bidirectional sold reconciliation: Tradera <-> Blocket & Facebook."""
    console.print(Panel("[bold green]Running Bidirectional Sold Reconciliation (Tradera <-> Blocket & Facebook)...[/bold green]"))
    from src.reconciliation.sold_checker import SoldReconciler
    reconciler = SoldReconciler()
    dry_run = getattr(args, "dry_run", False)
    headless = getattr(args, "headless", True)
    results = reconciler.reconcile_all(dry_run=dry_run, headless=headless)
    tradera_count = len(results.get("tradera_sales", []))
    external_count = len(results.get("external_sales", []))
    total = tradera_count + external_count
    if total == 0:
        console.print("[bold green][OK] No new sold items detected on any platform. Everything is in sync![/bold green]")
    else:
        console.print(f"[bold green][OK] Reconciled {total} item(s) (Tradera: {tradera_count}, External: {external_count})![/bold green]")

def main():
    parser = argparse.ArgumentParser(description="Tradera -> Blocket & Facebook Marketplace Item Trading Bot")
    subparsers = parser.add_subparsers(dest="command")

    # sync (one-click full pipeline)
    p_sync = subparsers.add_parser("sync", help="One-click pipeline: Fetch Tradera & Draft to Blocket and/or Facebook")
    p_sync.add_argument("--target", choices=["blocket", "facebook", "all"], default="blocket", help="Target marketplace (default: blocket)")
    p_sync.add_argument("--limit", type=int, help="Limit number of items to draft in this run")
    p_sync.add_argument("--headless", action="store_true", help="Run browser in background without visible window")

    # fetch
    subparsers.add_parser("fetch", help="Fetch active listings from Tradera")

    # list
    p_list = subparsers.add_parser("list", help="List tracked items and multi-platform sync status")

    # login (Blocket)
    subparsers.add_parser("login", help="Log in to Blocket and save session")

    # fb-login (Facebook)
    p_fblogin = subparsers.add_parser("fb-login", help="Log in to Facebook Marketplace and save session")
    p_fblogin.add_argument("--import", dest="import_chrome", action="store_true", help="Directly import active Facebook session from Chrome")
    p_fblogin.add_argument("--cdp", action="store_true", help="Connect to existing Chrome on port 9222 and export cookies")
    p_fblogin.add_argument("--c-user", help="Facebook c_user cookie (User ID)")
    p_fblogin.add_argument("--xs", help="Facebook xs cookie (Session token)")
    p_fblogin.add_argument("--cookies", help="Full cookie string containing c_user and xs")

    # draft (Blocket)
    p_draft = subparsers.add_parser("draft", help="Draft listing(s) on Blocket")
    p_draft.add_argument("--item-id", help="Draft a specific item by ID")
    p_draft.add_argument("--all", action="store_true", help="Draft all unsynced items")
    p_draft.add_argument("--limit", type=int, help="Limit number of items to draft")
    p_draft.add_argument("--delay", type=float, default=10.0, help="Seconds to wait between drafts (default: 10)")
    p_draft.add_argument("--headless", action="store_true", help="Run browser in background")

    # publish (Blocket direct publish)
    p_publish = subparsers.add_parser("publish", help="Publish listing(s) directly to Blocket (active ads)")
    p_publish.add_argument("--item-id", help="Publish a specific item by ID")
    p_publish.add_argument("--all", action="store_true", help="Publish all unsynced items")
    p_publish.add_argument("--limit", type=int, help="Limit number of items to publish")
    p_publish.add_argument("--delay", type=float, default=30.0, help="Seconds to wait between posts (default: 30)")
    p_publish.add_argument("--headless", action="store_true", help="Run browser in background")

    # fb-draft (Facebook)
    p_fbdraft = subparsers.add_parser("fb-draft", help="Draft listing(s) on Facebook Marketplace")
    p_fbdraft.add_argument("--item-id", help="Draft a specific item by ID")
    p_fbdraft.add_argument("--all", action="store_true", help="Draft all unsynced items")
    p_fbdraft.add_argument("--limit", type=int, help="Limit number of items to draft")
    p_fbdraft.add_argument("--delay", type=float, default=15.0, help="Seconds to wait between drafts (default: 15)")
    p_fbdraft.add_argument("--publish", action="store_true", help="Publish directly instead of saving draft")
    p_fbdraft.add_argument("--review", action="store_true", help="Pause in browser to review before submitting")
    p_fbdraft.add_argument("--headless", action="store_true", help="Run browser in background")

    # clean-drafts
    p_clean = subparsers.add_parser("clean-drafts", help="Delete all drafts from Blocket and reset sync status")
    p_clean.add_argument("--headless", action="store_true", default=True, help="Run browser in background")

    # set-price
    p_price = subparsers.add_parser("set-price", help="Set target price for an item")
    p_price.add_argument("item_id", help="Item ID")
    p_price.add_argument("price", type=int, help="Target price in SEK")

    # set-floor
    p_floor = subparsers.add_parser("set-floor", help="Set custom floor price for an item")
    p_floor.add_argument("item_id", help="Item ID")
    p_floor.add_argument("floor", type=int, help="Floor price in SEK (auto-rounded down to 9)")

    # ladder
    subparsers.add_parser("ladder", help="View pricing ladder stages and visual rotation status")

    # advance-ladder
    p_adv = subparsers.add_parser("advance-ladder", help="Advance item(s) along pricing ladder and rotate cover photo")
    p_adv.add_argument("--item-id", help="Item ID to advance")
    p_adv.add_argument("--all", action="store_true", help="Advance all items")

    # dedupe
    p_dedupe = subparsers.add_parser("dedupe", help="Scan and optionally merge duplicate listings")
    p_dedupe.add_argument("--merge", action="store_true", help="Automatically merge detected duplicates into primary listing")

    # tradera-login
    p_traderalogin = subparsers.add_parser("tradera-login", help="Log in to Tradera and save session state for unlisting")
    p_traderalogin.add_argument("--trd-at", help="Tradera access token cookie (trd_at JWT)")
    p_traderalogin.add_argument("--trd-rt", default="", help="Tradera refresh token cookie (trd_rt)")
    p_traderalogin.add_argument("--cookies", help="Full raw Cookie header string copied from tradera.com")


    # sync-sold
    p_sync_sold = subparsers.add_parser("sync-sold", help="Detect items sold on Tradera/Blocket and unlist cross-platform")
    p_sync_sold.add_argument("--dry-run", action="store_true", help="Preview items to unlist without deleting")
    p_sync_sold.add_argument("--headless", action="store_true", default=True, help="Run browser in background")

    args = parser.parse_args()

    # Default to sync if no command provided
    if not args.command:
        cmd_sync(argparse.Namespace(target="blocket", limit=None, headless=False))
        return

    commands = {
        "sync": cmd_sync,
        "sync-sold": cmd_sync_sold,
        "fetch": cmd_fetch,
        "list": cmd_list,
        "login": cmd_login,
        "tradera-login": cmd_tradera_login,
        "fb-login": cmd_fb_login,
        "draft": cmd_draft,
        "publish": cmd_publish,
        "fb-draft": cmd_fb_draft,
        "clean-drafts": cmd_clean_drafts,
        "set-price": cmd_set_price,
        "set-floor": cmd_set_floor,
        "ladder": cmd_ladder,
        "advance-ladder": cmd_advance_ladder,
        "dedupe": cmd_dedupe,
    }

    commands[args.command](args)

if __name__ == "__main__":
    main()


