import click

import bmg

VERSION = "v1"

print(f"yaBMGr {VERSION} by patataofcourse")

@click.group(help="converts BMG to RBMG and back",options_metavar='')
def cli():
    pass

@cli.command(   "unpack",
                help="converts a BMG into the readable format RBMG",
                no_args_is_help = True,
                options_metavar='[-o/--output OUTPUT]'
            )
@click.argument("input")
@click.option("-o", "--output", default=None)
def unpack(input, output):
    click.echo("test")

@cli.command(   "pack",
                help="converts a RBMG back into Nintendo's BMG",
                no_args_is_help = True,
                options_metavar='[-o/--output OUTPUT]'
            )
@click.argument("input")
@click.option("-o", "--output", default=None)
def pack(input, output):
    click.echo("test")

if __name__ == "__main__":
    cli()