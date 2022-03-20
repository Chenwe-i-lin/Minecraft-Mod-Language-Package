import re
import threading
import time
from enum import Enum

import requests

from src.baka_init import *

class Source(Enum):
    CurseForge = 1
    FTB = 2

# 获取模组信息的多线程类的构建
class GetProjectsFromPage(threading.Thread):
    # 初始化
    # mig_page_num：具体的页数
    # mode：模式（1：curseforge 模组区；2：feed the beast 整合区）
    def __init__(self, mig_page_num, source):
        threading.Thread.__init__(self)
        self.num = mig_page_num
        self.source = source

    # 主体程序
    def run(self):
        # 正式爬取
        if self.source == Source.CurseForge:
            mig_page = requests.get(
                f"https://www.curseforge.com/minecraft/mc-mods?filter-game-version={VERSION}&filter-sort=5&page={self.num}",
                headers=HEADERS,
                proxies=PROXIES,
            ).text


            # 正则抓取所有模组列表
            mig_list = re.findall(r'<a href="/minecraft/mc-mods/(.*?)/download" class="button button--hollow">', mig_page)
            MOD_LIST.extend(mig_list)

        if self.source == Source.FTB:
            # 按最近更新顺序排序，爬 FTB 新包
            modpack_info_get_page = requests.get(
                f"https://www.feed-the-beast.com/modpacks?filter-game-version={VERSION}&filter-sort=2&page={self.num}",
                headers=HEADERS,
                proxies=PROXIES,
            ).text


            # 正则抓取所有整合列表
            modpack_info_get_list = re.findall(r'<a href="/projects/(.*?)">', modpack_info_get_page)
            MODPACK_LIST.extend(modpack_info_get_list)


class ModpackModInfoGet(threading.Thread):
    # 初始化
    # mig_page：具体的页面
    def __init__(self, mmig_id, source):
        threading.Thread.__init__(self)
        self.id = mmig_id
        self.source = source

    # 主体程序
    def run(self):
        if self.source == Source.CurseForge:
            mmig_page = requests.get(
                f"https://www.curseforge.com/minecraft/modpacks/{self.id}/files/all?filter-game-version={VERSION}",
                headers=HEADERS,
                proxies=PROXIES,
            ).text

            mmig_list = re.findall(r'<a data-action="modpack-file-link" href="/minecraft/modpacks/.*?/files/(\d+)">' ,mmig_page)

            if len(mmig_list) != 0:
                mmig_file_page = requests.get(
                    f"https://www.curseforge.com/minecraft/modpacks/{self.id}/files/{mmig_list[0]}",
                    headers=HEADERS,
                    proxies=PROXIES,
                ).text

                mmig_modlist = re.findall(r'<a href="/minecraft/mc-mods/([^/]*)" class="truncate float-left w-full">', mmig_page)
                for mmig_n in mmig_modlist:
                    if mmig_n not in MOD_LIST and len(mmig_n) > 0:
                        MOD_LIST.append(mmig_n)
            return

        elif self.source == Source.FTB:
            url_var = "www.feed-the-beast.com"

        # 正式爬取
        mmig_page = requests.get(
            f"https://{url_var}/projects/{self.id}/files?filter-game-version={VERSION}",
            headers=HEADERS,
            proxies=PROXIES,
        ).text


        # 正则抓取该页面最新版整合
        mmig_list = re.findall(
            r'class="overflow-tip twitch-link" href="/projects/.*?/files/(\d+)"', mmig_page)

        # 似乎 FTB 网站只有 release 版的页面才会有模组列表
        mmit_release_type = re.findall(r'<div class="release-phase tip" title="Release">|<div class="beta-phase tip" title="Beta">', mmig_page)
        release_index = next(
            (
                i
                for i in range(len(mmit_release_type))
                if mmit_release_type[i]
                == '<div class="release-phase tip" title="Release">'
            ),
            -1,
        )

        # 提取出模组列表
        if release_index != -1 and len(mmig_list) > release_index:
            mmig_file_page = requests.get(
                f"https://{url_var}/projects/{self.id}/files/{mmig_list[release_index]}",
                headers=HEADERS,
                proxies=PROXIES,
            ).text


            # 正则抓取整合所使用的模组列表
            mmig_modlist = re.findall(r'<a href="/projects/(\d+)">', mmig_file_page)

            # 将数字 ID 翻译成语义化 ID
            for mmig_i in mmig_modlist:
                # 先转换下类型（否则后面的判定会因为类型不匹配而出现错误）
                mmig_i = int(mmig_i)

                # 转置映射表，因为要通过数字 ID 获取语义化 ID
                # 使用 copy 来复制 dict，否则可能会因为多线程原因发生 dictionary changed size during iteration 错误
                mmig_new_dict = {mmig_v: mmig_k for mmig_k, mmig_v in URL_ID_MAP.copy().items()}

                # asdflj 的列表并不完备，所有需要进一步检查列表的不完备性
                if mmig_i not in mmig_new_dict.keys():
                    # 获取重定向连接
                    mmig_url = requests.get(
                        f"https://www.feed-the-beast.com/projects/{mmig_i}",
                        headers=HEADERS,
                        proxies=PROXIES,
                    ).url

                    # 正则抓取处语义化 ID
                    mmig_match = re.findall(r'mc-mods/([^/]*)', mmig_url)
                    # 判定抓取情况，进行存储
                    if len(mmig_match) > 0:
                        logging.debug(f"源表中不存在的映射：{str(mmig_match)}")
                        mmig_new_dict[mmig_i] = mmig_match[0]
                        # 别忘记这个数据
                        URL_ID_MAP[mmig_match[0]] = mmig_i

                # 判定之前的模组列表中是否已经存在此模组，而后才进行装入
                # 发现可能会存入空数据，所有再进行一步判定
                if mmig_new_dict[mmig_i] not in MOD_LIST and len(mmig_new_dict[mmig_i]) > 0:
                    MOD_LIST.append(mmig_new_dict[mmig_i])


def main():
    logging.info("==================  模组列表获取函数开始  ==================")

    global MOD_LIST

    # 下面是逐个多线程获取信息的部分
    th_list = [
        GetProjectsFromPage(num, Source.CurseForge)
        for num in range(1, MOD_PAGE + 1)
    ]

    for th in th_list:
        # 延时 0.5 秒逐个启动线程
        th.start()
        time.sleep(0.5)
    for th in th_list:
        # 回收线程
        th.join()

    # 整合页面多线程
    th_list.clear()  # 打扫干净屋子再请客
    th_list.extend(
        GetProjectsFromPage(num, Source.FTB)
        for num in range(1, MODPACK_PAGE + 1)
    )

    for th in th_list:
        # 延时 0.5 秒逐个启动线程
        th.start()
        time.sleep(0.5)
    for th in th_list:
        # 回收线程
        th.join()

    # 整合中模组列表
    th_list.clear()  # 打扫干净屋子再请客
    # 从 asdflj 的 api 处获取文字 ID 和语义化 ID 的映射表
    # 从而方便获取整合中的模组列表
    # 此网站现已失效
    # URL_ID_MAP.update(requests.get("https://mc.meitangdehulu.com/message/mods_url_map"
    #                               "?api_key=" + ASDFLJ_API_KEY).json()["data"])
    # logging.info("从 asdflj 源中成功获取映射表")

    # 本地缓存的映射表，装入 URL_ID_MAP 中
    local_cache_map = CURSOR.execute("SELECT URL, ID from URL_ID_MAP")
    for row in local_cache_map:
        #if row[0] not in URL_ID_MAP.keys():
            # logging.debug("服务端 API 中不存在的映射：" + str(row))
        URL_ID_MAP[row[0]] = row[1]

    # 存入整合白名单
    MODPACK_LIST.extend(MODPACK_WHITELIST)
    logging.info(f"白名单整合已添加：{str(MODPACK_WHITELIST)}")

    # 剔除整合黑名单
    for i in MODPACK_LIST.copy():
        if i in MODPACK_BLACKLIST:
            MODPACK_LIST.remove(i)
    logging.info(f"黑名单整合已剔除：{str(MODPACK_BLACKLIST)}")

    for modpack in MODPACK_LIST:
        # 逐次放入线程
        source = Source.CurseForge if modpack in MODPACK_WHITELIST else Source.FTB
        th_list.append(ModpackModInfoGet(modpack, source))
    for th in th_list:
        # 延时 0.5 秒逐个启动线程
        th.start()
        time.sleep(0.5)
    for th in th_list:
        # 回收线程
        th.join()

    # 添加白名单
    MOD_LIST.extend(MOD_WHITELIST)
    logging.info(f"白名单已经添加进模组列表中：{str(MOD_WHITELIST)}")

    # 开始剔除黑名单
    for i in MOD_LIST.copy():
        if i in MOD_BLACKLIST:
            MOD_LIST.remove(i)
    logging.info(f"黑名单模组列表已剔除：{str(MOD_BLACKLIST)}")

    # 开始执行数据存储，出现错误则回滚
    try:
        MOD_LIST = sorted(set(MOD_LIST))
        with open(MOD_LIST_FILE, 'w') as f:
            f.write(json.dumps(MOD_LIST, indent=4, sort_keys=True))

        # 存储映射表
        for k, v in URL_ID_MAP.items():
            # API 获取的数据有可能为空，判定一下
            if len(k) > 0:
                CURSOR.execute(
                    f"INSERT OR IGNORE INTO URL_ID_MAP (URL, ID) VALUES ('{k}', {v});"
                )

        CONN.commit()

        # 存储模组列表
        for i in MODPACK_LIST:
            CURSOR.execute(f"INSERT OR IGNORE INTO MODPACK_LIST (URL) VALUES ('{i}');")
        CONN.commit()
        logging.info("数据存储完毕")
    except sqlite3.Error as sql_error:
        CONN.rollback()
        logging.fatal(f"数据存储失败：{str(sql_error)}")

    logging.info("==================  信息获取函数结束  ==================")


if __name__ == '__main__':
    main()
