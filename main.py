from anemoi.inference.config.run import RunConfiguration
from anemoi.inference.runners.default import DefaultRunner


def run():
    config = RunConfiguration.load('config.yaml')

    runner = DefaultRunner(config)

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
