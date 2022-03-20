import os
import shutil

from src.baka_init import *


def main(copy_from_path, copy_to_path):
    logging.info("==================  复制函数开始  ==================")

    # 先判定文件夹存在与否
    if not os.path.exists(f'{copy_to_path}/assets/'):
        return

    # 而后进行特定复制
    for i in os.listdir(f'{copy_to_path}/assets/'):
        logging.info(f"开始复制处理 {i} 模组")

        # 相关路径的构建
        to_en_us = f'{copy_to_path}/assets/{i}/lang/en_us.lang'
        to_zh_cn = f'{copy_to_path}/assets/{i}/lang/zh_cn.lang'
        to_zh_cn_old = f'{copy_to_path}/assets/{i}/lang/zh_cn_old.lang'
        to_en_us_old = f'{copy_to_path}/assets/{i}/lang/en_us_old.lang'

        # 补全其他文件，方便后续 handle
        if not os.path.isfile(to_en_us):
            open(to_en_us, "w").close()
        if not os.path.isfile(to_zh_cn):
            open(to_zh_cn, "w").close()
        if not os.path.isfile(to_en_us_old):
            open(to_en_us_old, "w").close()
        if not os.path.isfile(to_zh_cn_old):
            open(to_zh_cn_old, "w").close()

        # 遍历 weblate 语言文件所在的文件夹，复制指定的文件
        for j in os.listdir(f'{copy_from_path}/assets/'):
            # 相关路径的构建
            from_en_us = f'{copy_from_path}/assets/{j}/lang/en_us.lang'
            from_zh_cn = f'{copy_from_path}/assets/{j}/lang/zh_cn.lang'

            # 开始判定和复制
            # 先判定解压出来的是否存在英文文件
            if i == j:
                # en_us.lang -> en_us_old.lang
                if os.path.isfile(from_en_us):
                    shutil.copy(from_en_us, to_en_us_old)
                # zh_cn.lang -> zh_cn.lang
                if os.path.isfile(from_zh_cn):
                    shutil.copy(from_zh_cn, to_zh_cn)
                break

    logging.info("==================  复制函数结束  ==================")


if __name__ == '__main__':
    main("../../project", "../../tmp_assets")
