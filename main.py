import click
from anemoi.inference.config.run import RunConfiguration
from anemoi.inference.runners.default import DefaultRunner

@click.command()
@click.option('--config', type=click.Path(exists=True), default='config.yaml', help='Inference configuration file')
def cli(config: str):
    configuration = RunConfiguration.load(config)

    runner = DefaultRunner(configuration)

    import torch
    if torch.cuda.is_available():
        runner.device = "cuda"
    elif torch.backends.mps.is_available():
        runner.device = "mps"
    else:
        runner.device = "cpu"

    runner.execute()


if __name__ == '__main__':
    cli()
