import os
import base64
import io
import json
from collections import Counter
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体为黑体
plt.rcParams['axes.unicode_minus'] = False    # 正常显示负号



def collect_statistics_from_folder(input_folder):
    emotion_counter = Counter()
    type_counter = Counter()
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".json"):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'type' in data:
                            type_counter[data['type']] += 1
                        if '四元组' in data:
                            for item in data['四元组']:
                                if '情感' in item:
                                    emotion_counter[item['情感']] += 1
                except Exception as e:
                    print(f"Error reading {file}: {e}")
    return emotion_counter, type_counter

def plot_pie_chart(counter, title):
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    ax.pie(counter.values(), labels=counter.keys(), autopct='%1.1f%%', startangle=140)
    ax.set_title(title)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


#用来保存图片的，不用于web
def create_pie_chart(counter, title, output_file):
    if not counter:
        print(f"{title} 数据为空，未生成图像。")
        return
    labels = list(counter.keys())
    sizes = list(counter.values())

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"{title} 已保存为 {output_file}")

if __name__ == "__main__":
    folder_path = "./news_app/shantou_city/潮阳区"  # ← 这里替换成你的实际路径，例如 "./data"
    emotion_counts, type_counts = collect_statistics_from_folder(folder_path)

    create_pie_chart(emotion_counts, "情绪分布饼图", "emotion_pie.png")
    create_pie_chart(type_counts, "类型分布饼图", "type_pie.png")
