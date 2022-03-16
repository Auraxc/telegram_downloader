# !/usr/bin/env python3
import difflib
import os
import re
import time
import asyncio
import asyncio.subprocess
import logging
from telethon import TelegramClient, events, errors
from telethon.tl.types import MessageMediaWebPage, PeerChannel

# ***********************************************************************************#
api_id = 9944743  # your telegram api id
api_hash = 'f8075591229309e1e10f0502efc48a52'  # your telegram api hash
bot_token = '5276878860:AAGMbIbHgaIScfS4_wcticgSTMVKn8kRFac'  # your bot_token
admin_id = 1418580017  # your chat id
save_path = 'D:\\ttt'  # file save path
upload_file_set = False  # set upload file to google drive
drive_id = '5FyJClXmsqNw0-Rz19'  # google teamdrive id 如果使用OD，删除''内的内容即可。
drive_name = 'gc'  # rclone drive name
max_num = 5  # 同时下载数量
maxsize = 10*max_num
# filter file name/文件名过滤
filter_list = ['你好，欢迎加入 Quantumu', '\n']
# filter chat id /过滤某些频道不下载
blacklist = [1388464914, ]
download_all_chat = False  # 监控所有你加入的频道，收到的新消息如果包含媒体都会下载，默认关闭
filter_file_name = []  # 过滤文件后缀，可以填jpg、avi、mkv、rar等。
# proxy = ("socks5", '127.0.0.1', 1080)  # 自行替换代理设置，如果不需要代理，请删除括号内容
proxy = ("http", '127.0.0.1', 1081)  # 自行替换代理设置，如果不需要代理，请删除括号内容
# ***********************************************************************************#

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.ERROR)
logger = logging.getLogger(__name__)
queue = asyncio.Queue(maxsize=maxsize)


# 文件夹/文件名称处理
def validate_title(title):
    r_str = r"[\/\\\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    new_title = re.sub(r_str, "_", title)  # 替换为下划线
    return new_title


# 获取相册标题
async def get_group_caption(message):
    group_caption = ""
    entity = await client.get_entity(message.to_id)
    async for msg in client.iter_messages(entity=entity, reverse=True, offset_id=message.id - 9, limit=10):
        if msg.grouped_id == message.grouped_id:
            if msg.text != "":
                group_caption = msg.text
                return group_caption
    return group_caption


# 获取本地时间
def get_local_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# 判断相似率
def get_equal_rate(str1, str2):
    return difflib.SequenceMatcher(None, str1, str2).quick_ratio()


# 返回文件大小
def bytes_to_string(byte_count):
    suffix_index = 0
    while byte_count >= 1024:
        byte_count /= 1024
        suffix_index += 1

    return '{:.2f}{}'.format(
        byte_count, [' bytes', 'KB', 'MB', 'GB', 'TB'][suffix_index]
    )


def save_success(filename, offset_id=None):
    print("download finished", offset_id)
    with open("download_success.txt", "a+", encoding='utf8') as f:
        f.write("{}\n".format(filename))
        return


def read_file(path, mode):
    try:
        with open(path, mode, encoding='utf8') as f:
            return f.read()
    except FileNotFoundError as e:
        return ""


def check_file_exist(filename):
    text = read_file('download_success.txt', 'r')
    index = text.find(filename)
    if index != -1:
        print("file exist")
        return True
    return False


async def worker(name):
    while True:
        print("拿到文件")
        queue_item = await queue.get()
        message = queue_item[0]
        chat_title = queue_item[1]
        entity = queue_item[2]
        file_name = queue_item[3]
        offset_id = queue_item[4]
        for filter_file in filter_file_name:
            if file_name.endswith(filter_file):
                return
        dirname = validate_title(f'({entity.id})')
        datetime_dir_name = message.date.strftime("%Ya年%m月")
        file_save_path = os.path.join(save_path, dirname, datetime_dir_name)
        if not os.path.exists(file_save_path):
            os.makedirs(file_save_path)
        # 判断文件是否在本地存在
        if check_file_exist(file_name):
            print("{} 已下载, 跳过".format(offset_id))
            continue
        else:
            if file_name in os.listdir(file_save_path):
                os.remove(os.path.join(file_save_path, file_name))
            # os.remove(os.path.join(file_save_path, file_name))
        print(f"{get_local_time()} 开始下载 {offset_id}")
        try:
            print(f"start download {offset_id}")
            download_path = os.path.join(file_save_path, file_name)
            await client.download_media(message, download_path)
            print(f"stop download {offset_id}")

        except (errors.rpc_errors_re.FileReferenceExpiredError, asyncio.TimeoutError):
            logging.warning(f'{get_local_time()} - {offset_id} 出现异常，重新尝试下载！')
            # async for new_message in client.iter_messages(entity=entity, offset_id=message.id - 1, reverse=True,
            #                                               limit=1):
            await queue.put((message, chat_title, entity, file_name, message.id))
        except Exception as e:
            print(f"{get_local_time()} - {file_name} {e.__class__} {e}")
        finally:
            queue.task_done()


async def handler(name):
    try:
        print("start hander")
        chat_id = 'https://t.me/losslessflac'
        offset_id = 0
        try:
            entity = await client.get_entity(chat_id)
            chat_title = entity.title
            print(f'开始从第 {offset_id} 条消息下载')
        except ValueError:
            channel_id = chat_id.split('/')[-1]
            entity = await client.get_entity(PeerChannel(int(channel_id)))
            chat_title = entity.title
            print(f'开始从第 {offset_id} 条消息下载')
        except Exception as e:
            print('chat输入错误，请输入频道或群组的链接\n\n'
                               f'错误类型：{type(e).__class__}'
                               f'异常消息：{e}')
            return
        if chat_title:
            print(f'{get_local_time()} - 开始下载：({entity.id}) - {offset_id}')
            last_msg_id = 0
            async for message in client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=None):
                if message.media:
                    # 如果是一组媒体
                    caption = await get_group_caption(message) if (
                            message.grouped_id and message.text == "") else message.text
                    # 过滤文件名称中的广告等词语
                    if len(filter_list) and caption != "":
                        for filter_keyword in filter_list:
                            caption = caption.replace(filter_keyword, "")
                    # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
                    caption = "" if caption == "" else f'{validate_title(caption)} - '[
                                                       :50]
                    file_name = ''
                    # 如果是文件
                    if message.document:
                        if type(message.media) == MessageMediaWebPage:
                            continue
                        if message.media.document.mime_type == "image/webp":
                            continue
                        if message.media.document.mime_type == "application/x-tgsticker":
                            continue
                        for i in message.document.attributes:
                            try:
                                file_name = i.file_name
                            except:
                                continue
                        if file_name == '':
                            file_name = f'{message.id} - {caption}.{message.document.mime_type.split("/")[-1]}'
                        else:
                            # 如果文件名中已经包含了标题，则过滤标题
                            if get_equal_rate(caption, file_name) > 0.6:
                                caption = ""
                            file_name = f'{message.id} - {caption}{file_name}'
                    elif message.photo:
                        file_name = f'{message.id} - {caption}{message.photo.id}.jpg'
                    else:
                        continue
                    await queue.put((message, chat_title, entity, file_name, message.id))
                    last_msg_id = message.id
            print(admin_id, f'all message added to task queue, last message is：{last_msg_id}')
    except Exception as e:
        print("get error", e)
        exit(-1)


@events.register(events.NewMessage())
async def all_chat_download(update):
    message = update.message
    if message.media:
        chat_id = update.message.to_id
        entity = await client.get_entity(chat_id)
        if entity.id in blacklist:
            return
        chat_title = entity.title
        # 如果是一组媒体
        caption = await get_group_caption(message) if (
                message.grouped_id and message.text == "") else message.text
        if caption != "":
            for fw in filter_list:
                caption = caption.replace(fw, '')
        # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
        caption = "" if caption == "" else f'{validate_title(caption)} - '[:50]
        file_name = ''
        # 如果是文件
        if message.document:
            try:
                if type(message.media) == MessageMediaWebPage:
                    return
                if message.media.document.mime_type == "image/webp":
                    file_name = f'{message.media.document.id}.webp'
                if message.media.document.mime_type == "application/x-tgsticker":
                    file_name = f'{message.media.document.id}.tgs'
                for i in message.document.attributes:
                    try:
                        file_name = i.file_name
                    except:
                        continue
                if file_name == '':
                    file_name = f'{message.id} - {caption}.{message.document.mime_type.split("/")[-1]}'
                else:
                    # 如果文件名中已经包含了标题，则过滤标题
                    if get_equal_rate(caption, file_name) > 0.6:
                        caption = ""
                    file_name = f'{message.id} - {caption}{file_name}'
            except:
                print(message.media)
        elif message.photo:
            file_name = f'{message.id} - {caption}{message.photo.id}.jpg'
        else:
            return
        # 过滤文件名称中的广告等词语
        for filter_keyword in filter_list:
            file_name = file_name.replace(filter_keyword, "")
        print(chat_title, file_name)
        await queue.put((message, chat_title, entity, file_name, message.id))


if __name__ == '__main__':
    client = TelegramClient(
        'telegram_channel_downloader', api_id, api_hash, proxy=proxy).start()
    # if download_all_chat:
    #     client.add_event_handler(all_chat_download)
    tasks = []
    try:
        loop = asyncio.get_event_loop()
        for i in range(max_num):
            task = loop.create_task(worker(f'worker-{i}'))
            tasks.append(task)
        print('Successfully started (Press Ctrl+C to stop)')
        loop.create_task(handler(1))
        # handler()

        client.run_until_disconnected()
        print("after run until")
    finally:
        for task in tasks:
            task.cancel()
        client.disconnect()
        print('Stopped!')
