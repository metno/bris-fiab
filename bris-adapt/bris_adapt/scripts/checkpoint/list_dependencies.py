import click
import anemoi.inference

@click.command()
@click.argument('checkpoint_path', type=click.Path(exists=True))
def list_dependencies(checkpoint_path: str) -> None:
    '''List the dependencies of a bris domain checkpoint.'''

    checkpoint = anemoi.inference.checkpoint.Checkpoint(checkpoint_path)
    provenance = checkpoint.provenance_training()
    click.echo(f'Python version in checkpoint: {provenance["python"]}')

    click.echo('Anemoi module versions in checkpoint:')
    for name, version in provenance["module_versions"].items():
        if name.startswith('anemoi'):
            click.echo(f'    {name}: {version}')

    click.echo('Compare training environment from checkpoint with current environment:')
    checkpoint.validate_environment()
