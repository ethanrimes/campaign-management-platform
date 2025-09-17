# tests/test_execution_fetch.py

"""
Test script for fetching and displaying execution data.
Run with: python tests/test_execution_fetch.py [execution_id]
"""

import asyncio
import sys
import json
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich import print as rprint

# Add parent directory to path for imports
sys.path.append('.')

from backend.services.execution_data import ExecutionDataService
from backend.config.logging_config import LoggingConfig

# Initialize logging
LoggingConfig.setup_logging(log_level='INFO')

console = Console()


async def fetch_and_display_execution(execution_id: str):
    """Fetch and display execution data"""
    
    console.print(f"[bold cyan]Fetching execution data for: {execution_id}[/bold cyan]\n")
    
    service = ExecutionDataService()
    
    try:
        # Fetch the data
        with console.status("[bold green]Loading execution data..."):
            data = await service.get_execution_details(execution_id)
        
        if not data:
            console.print("[bold red]No data found for this execution ID[/bold red]")
            return
        
        # Display Summary
        summary = data.get('summary', {})
        summary_panel = Panel.fit(
            f"""[bold]Execution ID:[/bold] {summary.get('execution_id', 'N/A')}
[bold]Initiative ID:[/bold] {summary.get('initiative_id', 'N/A')}
[bold]Workflow Type:[/bold] {summary.get('workflow_type', 'N/A')}
[bold]Status:[/bold] {summary.get('status', 'N/A')}
[bold]Started:[/bold] {summary.get('started_at', 'N/A')}
[bold]Completed:[/bold] {summary.get('completed_at', 'N/A')}
[bold]Duration:[/bold] {summary.get('duration_seconds', 0):.2f} seconds
[bold]Steps Completed:[/bold] {', '.join(summary.get('steps_completed', []))}
[bold]Steps Failed:[/bold] {', '.join(summary.get('steps_failed', []))}""",
            title="[bold magenta]Execution Summary[/bold magenta]",
            border_style="magenta"
        )
        console.print(summary_panel)
        console.print()
        
        # Display Statistics Table
        stats_table = Table(title="[bold cyan]Content Statistics[/bold cyan]", show_header=True, header_style="bold cyan")
        stats_table.add_column("Type", style="green")
        stats_table.add_column("Count", justify="right", style="yellow")
        
        stats_table.add_row("Campaigns", str(len(data.get('campaigns', []))))
        stats_table.add_row("Ad Sets", str(len(data.get('adSets', []))))
        stats_table.add_row("Posts", str(len(data.get('posts', []))))
        stats_table.add_row("Research Entries", str(len(data.get('research', []))))
        stats_table.add_row("Media Files", str(len(data.get('mediaFiles', []))))
        
        console.print(stats_table)
        console.print()
        
        # Display Campaigns
        campaigns = data.get('campaigns', [])
        if campaigns:
            console.print("[bold green]📊 Campaigns:[/bold green]")
            for campaign in campaigns:
                tree = Tree(f"[bold]{campaign.get('name', 'Unnamed Campaign')}[/bold]")
                tree.add(f"ID: {campaign.get('id', 'N/A')}")
                tree.add(f"Objective: {campaign.get('objective', 'N/A')}")
                tree.add(f"Status: {campaign.get('status', 'N/A')}")
                tree.add(f"Budget: ${campaign.get('lifetime_budget', 0)}")
                tree.add(f"Description: {campaign.get('description', 'N/A')[:100]}...")
                console.print(tree)
            console.print()
        
        # Display Ad Sets
        ad_sets = data.get('adSets', [])
        if ad_sets:
            console.print("[bold blue]🎯 Ad Sets:[/bold blue]")
            for ad_set in ad_sets:
                tree = Tree(f"[bold]{ad_set.get('name', 'Unnamed Ad Set')}[/bold]")
                tree.add(f"ID: {ad_set.get('id', 'N/A')}")
                tree.add(f"Campaign ID: {ad_set.get('campaign_id', 'N/A')}")
                tree.add(f"Status: {ad_set.get('status', 'N/A')}")
                tree.add(f"Budget: ${ad_set.get('lifetime_budget', 0)}")
                
                # Target Audience
                if ad_set.get('target_audience'):
                    audience_tree = tree.add("Target Audience:")
                    audience = ad_set['target_audience']
                    if audience.get('age_range'):
                        audience_tree.add(f"Age: {audience['age_range'][0]}-{audience['age_range'][1]}")
                    if audience.get('locations'):
                        audience_tree.add(f"Locations: {', '.join(audience['locations'][:3])}")
                    if audience.get('interests'):
                        audience_tree.add(f"Interests: {', '.join(audience['interests'][:3])}")
                
                console.print(tree)
            console.print()
        
        # Display Posts
        posts = data.get('posts', [])
        if posts:
            console.print(f"[bold yellow]📝 Posts ({len(posts)} total):[/bold yellow]")
            for i, post in enumerate(posts[:3], 1):  # Show first 3 posts
                tree = Tree(f"[bold]Post {i}: {post.get('post_type', 'Unknown Type')}[/bold]")
                tree.add(f"ID: {post.get('id', 'N/A')}")
                tree.add(f"Status: {post.get('status', 'draft')}")
                tree.add(f"Published: {post.get('is_published', False)}")
                
                text = post.get('text_content', '')
                if text:
                    tree.add(f"Content: {text[:100]}...")
                
                hashtags = post.get('hashtags', [])
                if hashtags:
                    tree.add(f"Hashtags: {' '.join(hashtags[:5])}")
                
                media_urls = post.get('media_urls', [])
                if media_urls:
                    tree.add(f"Media: {len(media_urls)} file(s)")
                
                console.print(tree)
            
            if len(posts) > 3:
                console.print(f"[dim]... and {len(posts) - 3} more posts[/dim]")
            console.print()
        
        # Display Research
        research = data.get('research', [])
        if research:
            console.print("[bold magenta]🔍 Research:[/bold magenta]")
            for entry in research[:2]:  # Show first 2 research entries
                tree = Tree(f"[bold]{entry.get('topic', 'Unknown Topic')}[/bold]")
                tree.add(f"Type: {entry.get('research_type', 'N/A')}")
                tree.add(f"Summary: {(entry.get('summary', 'N/A')[:150])}...")
                
                insights = entry.get('insights', [])
                if insights:
                    insights_tree = tree.add(f"Insights ({len(insights)} total):")
                    for insight in insights[:2]:
                        insights_tree.add(f"• {insight.get('finding', 'N/A')[:100]}...")
                
                sources = entry.get('sources', [])
                if sources:
                    tree.add(f"Sources: {len(sources)} reference(s)")
                
                console.print(tree)
            
            if len(research) > 2:
                console.print(f"[dim]... and {len(research) - 2} more research entries[/dim]")
            console.print()
        
        # Display Media Files
        media_files = data.get('mediaFiles', [])
        if media_files:
            console.print(f"[bold cyan]🎨 Media Files ({len(media_files)} total):[/bold cyan]")
            media_table = Table(show_header=True, header_style="bold cyan")
            media_table.add_column("Type", style="green")
            media_table.add_column("Path", style="yellow")
            media_table.add_column("Prompt", style="white")
            
            for media in media_files[:5]:  # Show first 5 media files
                media_table.add_row(
                    media.get('file_type', 'N/A'),
                    media.get('supabase_path', 'N/A').split('/')[-1],
                    (media.get('prompt_used', 'N/A')[:50] + '...') if media.get('prompt_used') else 'N/A'
                )
            
            console.print(media_table)
            if len(media_files) > 5:
                console.print(f"[dim]... and {len(media_files) - 5} more media files[/dim]")
            console.print()
        
        # Option to save full JSON
        console.print("[bold]💾 Full data saved to: execution_data.json[/bold]")
        with open('execution_data.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
    except Exception as e:
        console.print(f"[bold red]Error fetching execution data: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())


async def list_recent_executions():
    """List recent executions to choose from"""
    service = ExecutionDataService()
    
    console.print("[bold cyan]Fetching recent executions...[/bold cyan]\n")
    
    try:
        summaries = await service.get_execution_summaries(limit=10)
        
        if not summaries:
            console.print("[bold red]No executions found[/bold red]")
            return None
        
        table = Table(title="[bold green]Recent Executions[/bold green]", show_header=True, header_style="bold green")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Execution ID", style="yellow")
        table.add_column("Workflow Type", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Started At", style="blue")
        table.add_column("Duration (s)", justify="right")
        
        for i, summary in enumerate(summaries, 1):
            status_color = "green" if summary['status'] == 'completed' else "red" if summary['status'] == 'failed' else "yellow"
            table.add_row(
                str(i),
                summary['execution_id'][:8] + '...',
                summary.get('workflow_type', 'unknown'),
                f"[{status_color}]{summary['status']}[/{status_color}]",
                summary.get('started_at', 'N/A')[:19],
                f"{summary.get('duration_seconds', 0):.1f}" if summary.get('duration_seconds') else 'N/A'
            )
        
        console.print(table)
        console.print()
        
        # Let user select
        choice = console.input("[bold cyan]Enter number to select (or full execution ID): [/bold cyan]")
        
        if choice.isdigit() and 1 <= int(choice) <= len(summaries):
            return summaries[int(choice) - 1]['execution_id']
        elif len(choice) > 20:  # Probably a full UUID
            return choice
        else:
            console.print("[bold red]Invalid selection[/bold red]")
            return None
            
    except Exception as e:
        console.print(f"[bold red]Error listing executions: {e}[/bold red]")
        return None


async def main():
    """Main entry point"""
    console.print(Panel.fit(
        "[bold cyan]Execution Data Fetcher[/bold cyan]\n"
        "Fetch and display all data related to a workflow execution",
        border_style="cyan"
    ))
    console.print()
    
    if len(sys.argv) > 1:
        # Execution ID provided as argument
        execution_id = sys.argv[1]
    else:
        # Show list and let user select
        execution_id = await list_recent_executions()
        
        if not execution_id:
            return
    
    await fetch_and_display_execution(execution_id)


if __name__ == "__main__":
    # Check for required packages
    try:
        import rich
    except ImportError:
        print("Please install rich: pip install rich")
        sys.exit(1)
    
    asyncio.run(main())