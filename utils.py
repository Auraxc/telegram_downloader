import re
import time
import difflib
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


def format_time(unix_time):
    date_time = unix_time.strftime("%Y-%d-%m %H:%M:%S")
    return date_time


# replace invalid characters, limit max length in 15
def validate_title(title):
    r_str = r"[\/\\\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    new_title = re.sub(r_str, "_", title)  # 替换为下划线
    return new_title[:15]
