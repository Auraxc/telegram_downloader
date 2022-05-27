# !/usr/bin/env python3

import os

import asyncio
import asyncio.subprocess
import logging
from telethon import TelegramClient, events, errors
from telethon.tl.types import MessageMediaWebPage, PeerChannel, MessageMediaPoll, DocumentAttributeAnimated, \
    MessageMediaDocument, DocumentAttributeVideo

# ***********************************************************************************#
from utils import validate_title, check_file_exist, get_local_time, format_time, get_equal_rate

api_id = 9944743  # your telegram api id
api_hash = 'f8075591229309e1e10f0502efc48a52'  # your telegram api hash
bot_token = '5276878860:AAGMbIbHgaIScfS4_wcticgSTMVKn8kRFac'  # your bot_token
admin_id = 1418580017  # your chat id
save_path = 'D:\\ttt'  # file save path
upload_file_set = False  # set upload file to google drive
drive_id = '5FyJClXmsqNw0-Rz19'  # google teamdrive id 如果使用OD，删除''内的内容即可。
drive_name = 'gc'  # rclone drive name
max_num = 1  # 同时下载数量
maxsize = 10 * max_num
# filter file name/文件名过滤
filter_list = ['你好，欢迎加入 Quantumu', '\n']
# filter chat id /过滤某些频道不下载
blacklist = [1388464914, ]
download_all_chat = False  # 监控所有你加入的频道，收到的新消息如果包含媒体都会下载，默认关闭
filter_suffixes = []  # 过滤文件后缀，可以填jpg、avi、mkv、rar等。
proxy = ("http", '127.0.0.1', 1081)  # 自行替换代理设置，如果不需要代理，请删除括号内容
# ***********************************************************************************#

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)

queue = asyncio.Queue(maxsize=maxsize)


class customMessage:
    def __init__(self, message, group_id=None, file_name='', text='', ):
        self.message = message
        self.file_name = file_name
        self.group_id = group_id
        self.text = text


# 获取相册标题
async def get_group_caption(message):
    group_caption = ""
    entity = await client.get_entity(message.to_id)
    async for msg in client.iter_messages(entity=entity, reverse=False, offset_id=message.id - 9, limit=10):
        if msg.grouped_id == message.grouped_id:
            if msg.text != "":
                group_caption = msg.text
                return group_caption
    print('group_caption', group_caption)
    return group_caption


def save_success(filename, offset_id=None):
    print("download finished", offset_id)
    with open("download_success.txt", "a+", encoding='utf8') as f:
        f.write("{}\n".format(filename))
        return


async def worker():
    while True:
        queue_item = await queue.get()
        message, chat_title, entity, file_name, offset_id = queue_item
        message, file_name, offset_id = queue_item
        # chat_title = queue_item[1]
        # entity = queue_item[2]
        # file_name = queue_item[3]
        # offset_id = queue_item[4]

        dirname = validate_title(f'({entity.id})')
        datetime_dir_name = message.date.strftime("%Ya - %m")
        file_save_path = os.path.join(save_path, dirname, datetime_dir_name)
        if not os.path.exists(file_save_path):
            os.makedirs(file_save_path)

        if check_file_exist(file_name):
            print("{} finished, pass".format(offset_id))
            continue
        else:
            if file_name in os.listdir(file_save_path):
                os.remove(os.path.join(file_save_path, file_name))
            # os.remove(os.path.join(file_save_path, file_name))
        print(f"{get_local_time()} 开始下载 {offset_id}")
        try:
            print(f"start download {offset_id}")
            _download_path = os.path.join(file_save_path, file_name)
            await client.download_media(message, _download_path)
            print(f"stop download {offset_id}")

        except (errors.rpc_errors_re.FileReferenceExpiredError, asyncio.TimeoutError):
            logging.warning(f'{get_local_time()} - {offset_id} 出现异常，重新尝试下载！')
            await queue.put((message, chat_title, entity, file_name, message.id))
        except Exception as e:
            print(f"{get_local_time()} - {file_name} {e.__class__} {e}")
        finally:
            queue.task_done()


async def get_entity(chat_id):
    # get channel info
    try:
        channel_id = chat_id.split('/')[-1]

        if channel_id.isdigit():
            entity = await client.get_entity(PeerChannel(int(channel_id)))
        else:
            entity = await client.get_entity(chat_id)

        return entity
    except Exception as e:
        raise ValueError(f'chat_id incorrect, check and run again\r\nerror info：{e}')


# async def add_job_to_queue(entity, offset_id):
#     try:
#         last_msg_id = 0
#         async for message in client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=None):
#             if message.media:
#                 # 如果是一组媒体
#                 caption = await get_group_caption(message) if (
#                         message.grouped_id and message.text == "") else message.text
#                 # 过滤文件名称中的广告等词语
#                 if len(filter_list) and caption != "":
#                     for filter_keyword in filter_list:
#                         caption = caption.replace(filter_keyword, "")
#                 # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
#                 caption = "" if caption == "" else f'{validate_title(caption)} - '[
#                                                    :50]
#                 file_name = ''
#                 # 如果是文件
#                 if message.document:
#                     if type(message.media) == MessageMediaWebPage:
#                         continue
#                     if message.media.document.mime_type == "image/webp":
#                         continue
#                     if message.media.document.mime_type == "application/x-tgsticker":
#                         continue
#                     for i in message.document.attributes:
#                         try:
#                             file_name = i.file_name
#                         except:
#                             continue
#                     if file_name == '':
#                         file_name = f'{message.id} - {caption}.{message.document.mime_type.split("/")[-1]}'
#                     else:
#                         # 如果文件名中已经包含了标题，则过滤标题
#                         if get_equal_rate(caption, file_name) > 0.6:
#                             caption = ""
#                         file_name = f'{message.id} - {caption}{file_name}'
#                 elif message.photo:
#                     file_name = f'{message.id} - {caption}{message.photo.id}.jpg'
#                 else:
#                     continue
#                 await queue.put((message, chat_title, entity, file_name, message.id))
#                 last_msg_id = message.id
#         print(admin_id, f'all message added to task queue, last message is：{last_msg_id}')
#     except Exception as e:
#         print("e", e)
# async def process_filename(media, media_type):
#     media_type = media.document.mime_type
#     filename = f'{media.id} - '
#     pass


# async def process_group_media(medias, text):
#     base_filename = validate_title(text)
#     for media in medias:
#         filename = f'{media.id} - {base_filename} - '


async def add_to_queue(c):
    return await queue.put((c.message, c.chat_title, c.entity, c.file_name, c.message.id))


def filename_filter(filename):
    filters = ['sticker.webp']
    if filename in filters:
        return False
    for suffix in filter_suffixes:
        if filename.endswith(suffix):
            return False
    return filename


def _create_filename(message):
    photo = message.photo
    document = message.document
    grouped_id = message.grouped_id
    filename = ''
    if photo:
        base_name = format_time(photo.date)
        filename = f'{message.id} - {base_name}.jpg'
        if grouped_id:
            filename = f"{grouped_id} - {filename}"
    elif document:
        filename = f'{message.id} - {document.attributes[-1].file_name}'
    filename = filename_filter(filename)
    return filename


def filename_from_media(message):
    if not message.media:
        return False
    media = message.media
    if isinstance(media, MessageMediaDocument):
        attribute = media.document.attributes[-1]
        if isinstance(attribute, DocumentAttributeAnimated) or isinstance(attribute, DocumentAttributeVideo):
            return False
    if isinstance(media, MessageMediaPoll):
        return False
    filename = _create_filename(message)
    return filename


def download_path(entity, message, filename):
    dirname = validate_title(f'{entity.title}({entity.id})')
    datetime_dir_name = message.date.strftime("%Ya - %m")
    file_save_path = os.path.join(save_path, dirname, datetime_dir_name)
    if not os.path.exists(file_save_path):
        os.makedirs(file_save_path)

    _download_path = os.path.join(file_save_path, filename)

    if check_file_exist(filename):
        print("{} finished, pass".format(filename))
        return False
    else:
        if os.path.exists(_download_path):
            os.remove(_download_path)
        # os.remove(os.path.join(file_save_path, file_name))
    return _download_path


async def handler(name='handler'):
    try:
        # chat_id = 'https://t.me/losslessflac'
        chat_id = 'https://t.me/musicalossless'
        offset_id = 0

        entity = await get_entity(chat_id)
        chat_title = entity.title
        logging.info(f'start download ({chat_title}) from offset ({offset_id})')
        last_msg_id = 0
        # TODO: add reverse download, use reverse config
        message_iter = client.iter_messages(entity, offset_id=offset_id, reverse=False, limit=None)
        async for message in message_iter:
            filename = filename_from_media(message)
            if filename:
                path = download_path(entity, message, filename)
                if path:
                    await queue.put((message, download_path, message.id))
                    # custom_message = customMessage(message=message, text=message.text[:15])
            last_msg_id = message.id
        print(admin_id, f'all message added to task queue, last message is：{last_msg_id}')
    except Exception as e:
        print(e)


@events.register(events.NewMessage())
async def all_chat_download(update):
    message = update.message
    if message.media:
        chat_id = update.message.to_id
        entity = await client.get_entity(chat_id)
        if entity.id in blacklist:
            logging.warning(f'entity ({entity.id}) in black list, pass')
            return
        chat_title = entity.title
        # 如果是一组媒体
        caption = await get_group_caption(message) if (
                message.grouped_id and message.text == "") else message.text
        print("caption", caption)
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
                    except Exception as e:
                        print("error", e)
                        continue
                if file_name == '':
                    file_name = f'{message.id} - {caption}.{message.document.mime_type.split("/")[-1]}'
                else:
                    # 如果文件名中已经包含了标题，则过滤标题
                    if get_equal_rate(caption, file_name) > 0.6:
                        caption = ""
                    file_name = f'{message.id} - {caption}{file_name}'
            except Exception as e:
                print(message.media, e)
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
    tasks = []
    try:
        loop = asyncio.get_event_loop()
        # for i in range(max_num):
        #     task = loop.create_task(worker(f'worker-{i}'))
        #     tasks.append(task)
        # print('worker ready,waiting for download')

        loop.create_task(handler())
        client.run_until_disconnected()
    finally:
        for task in tasks:
            task.cancel()
        client.disconnect()
        print('Stopped!')
