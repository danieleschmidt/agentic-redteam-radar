"""
Command-line interface for Agentic RedTeam Radar.

Provides a rich CLI for running security scans against AI agents.
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Optional, List
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text

from .scanner import RadarScanner
from .agent import create_agent, AgentType
from .config import RadarConfig
from .results import ScanResult
from .utils.logger import setup_logger


console = Console()


def print_banner():
    """Print the application banner."""
    banner = """
[bold red]🎯 Agentic RedTeam Radar[/bold red]
[dim]Open-source AI agent security testing framework[/dim]
[dim]Version 0.1.0 | MIT License[/dim]
"""
    console.print(Panel(banner, border_style="red"))


@click.group()
@click.version_option(version="0.1.0")
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config', type=click.Path(), help='Configuration file path')
@click.pass_context
def cli(ctx, debug, config):
    """Agentic RedTeam Radar - AI Agent Security Testing Framework."""
    ctx.ensure_object(dict)
    
    # Setup logging
    log_level = "DEBUG" if debug else "INFO"
    ctx.obj['logger'] = setup_logger("agentic_redteam.cli", log_level)
    
    # Load configuration
    if config:
        ctx.obj['config'] = RadarConfig.from_file(config)
    else:
        ctx.obj['config'] = RadarConfig.from_env()
    
    if debug:
        ctx.obj['config'].log_level = "DEBUG"
        ctx.obj['config'].enable_debug = True


@cli.command()
@click.option('--agent-name', required=True, help='Name of the agent to scan')
@click.option('--agent-type', 
              type=click.Choice(['openai_gpt', 'anthropic_claude', 'custom']),
              required=True, help='Type of agent')
@click.option('--model', required=True, help='Model name (e.g., gpt-4, claude-3)')
@click.option('--system-prompt', help='System prompt for the agent')
@click.option('--api-key', help='API key for the agent (or set OPENAI_API_KEY/ANTHROPIC_API_KEY)')
@click.option('--patterns', help='Comma-separated list of patterns to run')
@click.option('--output', type=click.Path(), help='Output file path')
@click.option('--format', 'output_format', 
              type=click.Choice(['json', 'yaml', 'html']),
              default='json', help='Output format')
@click.option('--fail-on', 
              type=click.Choice(['critical', 'high', 'medium', 'low']),
              help='Exit with error if vulnerabilities of this severity or higher are found')
@click.pass_context
def scan(ctx, agent_name, agent_type, model, system_prompt, api_key, 
         patterns, output, output_format, fail_on):
    """Run security scan against an AI agent."""
    
    print_banner()
    logger = ctx.obj['logger']
    config = ctx.obj['config']
    
    try:
        # Update config with CLI options
        if patterns:
            config.enabled_patterns = [p.strip() for p in patterns.split(',')]
        if output_format:
            config.output_format = output_format
        if fail_on:
            config.fail_on_severity = fail_on
        
        # Create agent
        console.print(f"\n[bold blue]Creating agent:[/bold blue] {agent_name}")
        
        agent_kwargs = {
            'api_key': api_key,
            'system_prompt': system_prompt
        }
        
        agent = create_agent(agent_name, agent_type, model, **agent_kwargs)
        
        # Validate agent
        console.print("[bold blue]Validating agent...[/bold blue]")
        from .utils.validators import validate_agent
        validation_errors = validate_agent(agent)
        
        if validation_errors:
            console.print("[bold red]Agent validation failed:[/bold red]")
            for error in validation_errors:
                console.print(f"  ❌ {error}")
            sys.exit(1)
        
        console.print("  ✅ Agent validation passed")
        
        # Create scanner
        scanner = RadarScanner(config)
        
        # Show scan configuration
        console.print(f"\n[bold blue]Scan Configuration:[/bold blue]")
        console.print(f"  Patterns: {', '.join(config.enabled_patterns)}")
        console.print(f"  Concurrency: {config.max_concurrency}")
        console.print(f"  Timeout: {config.timeout}s")
        
        # Run scan with progress tracking
        console.print(f"\n[bold blue]Starting security scan...[/bold blue]")
        
        def progress_callback(progress_info):
            """Update progress display."""
            pass  # Progress handled by rich progress bar
        
        # Use asyncio to run the scan
        result = asyncio.run(run_scan_with_progress(scanner, agent, progress_callback))
        
        # Display results
        display_scan_results(result)
        
        # Save results if output path specified
        if output:
            save_results(result, output, config.output_format)
            console.print(f"\n💾 Results saved to: [bold]{output}[/bold]")
        
        # Check if we should fail based on severity
        if should_fail_on_severity(result, config.fail_on_severity):
            console.print(f"\n[bold red]❌ Scan failed: Found vulnerabilities of severity '{config.fail_on_severity}' or higher[/bold red]")
            sys.exit(1)
        else:
            console.print(f"\n[bold green]✅ Scan completed successfully[/bold green]")
    
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        console.print(f"\n[bold red]❌ Scan failed: {e}[/bold red]")
        sys.exit(1)


async def run_scan_with_progress(scanner, agent, progress_callback):
    """Run scan with rich progress display."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        
        # Add progress task
        task = progress.add_task("Running security scan...", total=100)
        
        # Track progress
        def update_progress(progress_info):
            progress.update(task, completed=progress_info.progress_percentage)
            progress.update(task, description=f"Scanning... ({progress_info.completed_patterns}/{progress_info.total_patterns} patterns)")
        
        # Run the scan
        result = await scanner.scan(agent, update_progress)
        progress.update(task, completed=100, description="Scan completed")
        
        return result


def display_scan_results(result: ScanResult):
    """Display scan results in a formatted table."""
    
    stats = result.statistics
    
    # Summary table
    summary_table = Table(title="Scan Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")
    
    summary_table.add_row("Agent Name", result.agent_name)
    summary_table.add_row("Scan Duration", f"{result.scan_duration:.2f}s")
    summary_table.add_row("Patterns Executed", str(result.patterns_executed))
    summary_table.add_row("Total Tests", str(result.total_tests))
    summary_table.add_row("Total Vulnerabilities", str(len(result.vulnerabilities)))
    summary_table.add_row("Risk Score", f"{stats.get_risk_score():.2f}/10.0")
    
    console.print("\n")
    console.print(summary_table)
    
    # Vulnerabilities by severity
    if result.vulnerabilities:
        vuln_table = Table(title="Vulnerabilities by Severity", show_header=True, header_style="bold red")
        vuln_table.add_column("Severity", style="cyan")
        vuln_table.add_column("Count", style="white")
        
        severity_colors = {
            "critical": "bold red",
            "high": "red", 
            "medium": "yellow",
            "low": "blue",
            "info": "dim"
        }
        
        for severity, count in stats.vulnerabilities_by_severity.items():
            if count > 0:
                color = severity_colors.get(severity, "white")
                vuln_table.add_row(
                    Text(severity.upper(), style=color),
                    Text(str(count), style=color)
                )
        
        console.print("\n")
        console.print(vuln_table)
        
        # Detailed vulnerabilities
        if len(result.vulnerabilities) <= 10:  # Only show details for small numbers
            detail_table = Table(title="Vulnerability Details", show_header=True, header_style="bold yellow")
            detail_table.add_column("Name", style="cyan")
            detail_table.add_column("Category", style="white")
            detail_table.add_column("Severity", style="white")
            detail_table.add_column("Confidence", style="white")
            
            for vuln in result.vulnerabilities:
                severity_color = severity_colors.get(vuln.severity.value, "white")
                detail_table.add_row(
                    vuln.name,
                    vuln.category.value,
                    Text(vuln.severity.value.upper(), style=severity_color),
                    f"{vuln.confidence:.2f}"
                )
            
            console.print("\n")
            console.print(detail_table)


def save_results(result: ScanResult, output_path: str, format_type: str):
    """Save scan results to file."""
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    if format_type == 'json':
        with open(output_file, 'w') as f:
            f.write(result.to_json())
    elif format_type == 'yaml':
        import yaml
        with open(output_file, 'w') as f:
            yaml.dump(result.to_dict(), f, default_flow_style=False)
    elif format_type == 'html':
        from ..reporting.html_generator import generate_html_report
        html_content = generate_html_report(result)
        with open(output_file, 'w') as f:
            f.write(html_content)


def should_fail_on_severity(result: ScanResult, fail_severity: str) -> bool:
    """Check if scan should fail based on vulnerability severity."""
    
    if not fail_severity:
        return False
    
    severity_levels = {
        "info": 0,
        "low": 1,
        "medium": 2, 
        "high": 3,
        "critical": 4
    }
    
    fail_level = severity_levels.get(fail_severity.lower(), 4)
    
    for vuln in result.vulnerabilities:
        vuln_level = severity_levels.get(vuln.severity.value.lower(), 0)
        if vuln_level >= fail_level:
            return True
    
    return False


@cli.command()
@click.option('--output', type=click.Path(), default='radar-config.yaml', 
              help='Output configuration file path')
@click.pass_context
def init_config(ctx, output):
    """Initialize a new configuration file."""
    
    config = RadarConfig()
    config.save_to_file(output)
    
    console.print(f"[bold green]✅ Configuration saved to: {output}[/bold green]")
    console.print("\nEdit the configuration file to customize scanner behavior.")


@cli.command()
@click.pass_context
def list_patterns(ctx):
    """List available attack patterns."""
    
    config = ctx.obj['config']
    scanner = RadarScanner(config)
    
    patterns_table = Table(title="Available Attack Patterns", show_header=True, header_style="bold blue")
    patterns_table.add_column("Pattern", style="cyan")
    patterns_table.add_column("Enabled", style="white")
    
    for pattern_name in scanner.list_patterns():
        enabled = "✅" if config.is_pattern_enabled(pattern_name) else "❌"
        patterns_table.add_row(pattern_name, enabled)
    
    console.print(patterns_table)


@cli.command()
@click.argument('pattern_name')
@click.pass_context
def pattern_info(ctx, pattern_name):
    """Get detailed information about a specific pattern."""
    
    config = ctx.obj['config']
    scanner = RadarScanner(config)
    
    pattern_info = scanner.get_pattern_info(pattern_name)
    
    if not pattern_info:
        console.print(f"[bold red]❌ Pattern '{pattern_name}' not found[/bold red]")
        sys.exit(1)
    
    info_table = Table(title=f"Pattern: {pattern_name}", show_header=True, header_style="bold green")
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="white")
    
    for key, value in pattern_info.items():
        if isinstance(value, list):
            value = ", ".join(value) if value else "None"
        info_table.add_row(key.replace('_', ' ').title(), str(value))
    
    console.print(info_table)


def main():
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()