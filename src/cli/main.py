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

    for idx, card in enumerate(cards, 1):
        try:
            detail = client.get_item_detail(card.url, delay_seconds=0.2)
            if detail.buy_now_price is None and card.buy_now_price is not None:
                detail.buy_now_price = card.buy_now_price
            if detail.starting_price is None and card.starting_price is not None:
                detail.starting_price = card.starting_price

            is_new = repo.upsert_item(detail)
            if is_new:
                new_count += 1
            else:
                updated_count += 1
        except Exception as e:
            console.print(f"[red]Error fetching {card.url}: {e}[/red]")

    console.print(f"• Discovered: [bold]{new_count}[/bold] new, [bold]{updated_count}[/bold] refreshed.")
    return new_count, updated_count

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
    session_mgr.interactive_login(email="andreas.ahrlund@gmail.com")

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
                on_success=lambda i_id, url: repo.update_status(i_id, "drafted", blocket_ad_url=url)
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
    console.print(Panel(f"[bold green]Successfully deleted {count} drafts from Blocket and reset local database statuses to 'discovered'![/bold green]"))

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

    args = parser.parse_args()

    # Default to sync if no command provided
    if not args.command:
        cmd_sync(argparse.Namespace(target="blocket", limit=None, headless=False))
        return

    commands = {
        "sync": cmd_sync,
        "fetch": cmd_fetch,
        "list": cmd_list,
        "login": cmd_login,
        "fb-login": cmd_fb_login,
        "draft": cmd_draft,
        "publish": cmd_publish,
        "fb-draft": cmd_fb_draft,
        "clean-drafts": cmd_clean_drafts,
        "set-price": cmd_set_price,
    }

    commands[args.command](args)

if __name__ == "__main__":
    main()


