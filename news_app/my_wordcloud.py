import jieba
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import os
import json



def load_text_from_jsons(folder_path):
    text_parts = []

    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            file_path = os.path.join(folder_path, filename)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # 提取摘要
                    summary = data.get("摘要", "")
                    if summary:
                        text_parts.append(summary)
                        
                    news_type = data.get("type", "")
                    if news_type:
                        text_parts.append(news_type)

                    # 提取四元组
                    quads = data.get("四元组", [])
                    for quad in quads:
                        entity1 = quad.get("实体1", "")
                        event = quad.get("事件", "")
                        entity2 = quad.get("实体2", "")
                        emotion = quad.get("情感", "")
                        
                        # 将四元组转为文本，如：“实体1 事件 实体2 情感”
                        quad_text = f"{entity1} {event} {entity2} {emotion}"
                        text_parts.append(quad_text)

            except Exception as e:
                print(f"无法处理文件 {file_path}: {e}")

    # 合并所有文本片段
    text = " ".join(text_parts)
    return text

def creat_wordcloud(text):
    # 使用jieba分词处理文本
    cut_text = " ".join(jieba.cut(text))

    # 加载遮罩图像并处理
    mask_image = np.array(Image.open("mask.png"))  # 替换为实际的遮罩图像路径

    # 创建词云，指定遮罩图像（mask），字体，背景颜色等
    wordcloud = WordCloud(
        font_path="./SIMLI.TTF",  # 替换为实际的字体文件路径
        width=256,
        height=256,
        background_color="white",
        mask=mask_image,  # 使用图像作为词云形状
        max_words=200,
        contour_width=1,  # 轮廓宽度
        contour_color='black'  # 轮廓颜色
    ).generate(cut_text)
    
    wordcloud_img=wordcloud.to_image()
    
    # 获取原图尺寸
    width, height = wordcloud_img.size

    # 计算裁剪区域
    upper_crop = int(height * 0.25)              # 上面裁掉1/4
    lower_crop = int(height * (1 - 1 / 6))       # 下面裁掉1/5（保留前4/5）

    # 裁剪图片
    cropped_img = wordcloud_img.crop((0, upper_crop, width, lower_crop))

    
    return cropped_img

def wordcloud_process(folder_path):
    # 读取文件夹中的所有json文件
    text = load_text_from_jsons(folder_path)
    wordcloud = creat_wordcloud(text)
    return wordcloud
    

if __name__ == "__main__":
    # 生成词云
    # 准备文本
    #text = "雨后有车驶来驶过暮色苍白旧铁皮往南开 恋人已不在收听浓烟下的诗歌电台不动情的咳嗽 至少看起来归途也还可爱琴弦少了姿态再不见那夜里听歌的小孩时光匆匆独白将颠沛磨成卡带已枯卷的情怀踏碎成年代就老去吧 孤独别醒来你渴望的离开只是无处停摆就歌唱吧 眼睛眯起来而热泪的崩坏只是没抵达的存在青春又醉倒在籍籍无名的怀靠嬉笑来虚度聚散得慷慨辗转却去不到对的站台如果漂泊是成长必经的路牌你迷醒岁月中那贫瘠的未来像遗憾季节里未结果的爱弄脏了每一页诗吻最疼痛的告白而风声吹到这已不需要释怀就老去吧 孤独别醒来你渴望的离开只是无处停摆就歌唱吧 眼睛眯起来而热泪的崩坏只是没抵达的存在就甜蜜地忍耐繁星润湿窗台光影跳动着像在困倦里说爱再无谓的感慨以为明白梦倒塌的地方今已爬满青苔"
    text= load_text_from_jsons("./test_json_file")  # 替换为实际的文件夹路径
    #print(text)
    wordcloud = creat_wordcloud(text)


    #显示词云
    plt.figure(figsize=(10, 10))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')  # 不显示坐标轴
    plt.show()
