import logging.config
def fake_file_config(*args, **kwargs):
    pass
logging.config.fileConfig = fake_file_config 