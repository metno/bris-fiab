import click
from anemoi.inference.config.run import RunConfiguration
from anemoi.inference.runners.default import DefaultRunner
import earthkit.data as ekd




@click.command()
@click.option('--config', type=click.Path(exists=True), default='config.yaml', help='Inference configuration file')
def run(config: str):
    '''Run inference based on a provided configuration file.'''
    configuration = RunConfiguration.load(config)

    ekd.config.set("cache-policy", "user")

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
    run()
