from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

config = TemplateMinerConfig()
config.load("drain3.ini")  # 默认配置
template_miner = TemplateMiner(config=config)

def parse_log_line(line: str):
    result = template_miner.add_log_message(line)
    return {
        "raw": line,
        "template": result["template_mined"],
        "params": result["parameters"]
    }