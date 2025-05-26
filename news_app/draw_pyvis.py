import os
import json
from pyvis.network import Network
from IPython.display import IFrame

#这个是生成中间件的函数
def draw_quadruple_graph_from_folders(folder_paths, output_file="./static/three_quadruple_graph.html", height="1000px"):
    net = Network(height=height, width="100%", directed=True, notebook=True, cdn_resources='in_line')
    net.barnes_hut()
    added_nodes = set()

    for folder_path in folder_paths:
        if not os.path.isdir(folder_path):
            print(f"警告：路径 {folder_path} 不是有效的文件夹，已跳过。")
            continue

        # 遍历当前文件夹下所有 .json 文件
        for filename in os.listdir(folder_path):
            if filename.endswith(".json"):
                filepath = os.path.join(folder_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    quadruples = data.get("四元组", [])

                    for quad in quadruples:
                        ent1 = quad.get("实体1", "").strip()
                        event = quad.get("事件", "").strip()
                        ent2 = quad.get("实体2", "").strip()
                        sentiment = quad.get("情感", "").strip()

                        if not (ent1 and ent2 and event and sentiment):
                            continue

                        # 根据情感设置实体2颜色
                        if "负面" in sentiment or "消极" in sentiment:
                            ent2_color = "orange"
                        elif "正面" in sentiment or "积极" in sentiment:
                            ent2_color = "green"
                        else:
                            ent2_color = "lightblue"

                        # 添加实体1节点
                        if ent1 not in added_nodes:
                            net.add_node(ent1, label=ent1, color="lightblue")
                            added_nodes.add(ent1)

                        # 添加实体2节点
                        if ent2 not in added_nodes:
                            net.add_node(ent2, label=ent2, color=ent2_color)
                            added_nodes.add(ent2)

                        # 添加边，标签为 事件 + 情感
                        edge_label = f"{event} + {sentiment}"
                        net.add_edge(ent1, ent2, label=edge_label)

    net.set_options("""
    var options = {
        "nodes": {
            "font": {
                "size": 13
            }
        },
        "edges": {
            "font": {
                "size": 10
            }
        }
    }
    """)
    net.show(output_file)
    return IFrame(output_file, width="100%", height=height)

#这个是直接嵌入的函数
def generate_quadruple_graph_html(folder_paths, height="1000px"):
    net = Network(height=height, width="100%", directed=True, notebook=False, cdn_resources='in_line')
    net.barnes_hut()
    added_nodes = set()

    for folder_path in folder_paths:
        if not os.path.isdir(folder_path):
            print(f"警告：路径 {folder_path} 不是有效的文件夹，已跳过。")
            continue

        for filename in os.listdir(folder_path):
            print("正在处理文件:", filename)
            if filename.endswith(".json"):
                filepath = os.path.join(folder_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    this_url=data.get('link')
                    quadruples = data.get("四元组", [])

                    for quad in quadruples:
                        ent1 = quad.get("实体1", "").strip()
                        event = quad.get("事件", "").strip()
                        ent2 = quad.get("实体2", "").strip()
                        sentiment = quad.get("情感", "").strip()

                        if not (ent1 and ent2 and event and sentiment):
                            continue

                        if "负面" in sentiment or "消极" in sentiment:
                            ent2_color = "orange"
                        elif "正面" in sentiment or "积极" in sentiment:
                            ent2_color = "green"
                        else:
                            ent2_color = "lightblue"

                        if ent1 not in added_nodes:
                            net.add_node(ent1, label=ent1, color="lightblue")
                            added_nodes.add(ent1)

                        if ent2 not in added_nodes:
                            net.add_node(ent2, label=ent2, color=ent2_color)
                            added_nodes.add(ent2)

                        edge_label = f"{event} + {sentiment}"
                        net.add_edge(ent1, ent2, label=edge_label)

    net.set_options("""
    var options = {
        "nodes": {
            "font": {
                "size": 13
            }
        },
        "edges": {
            "font": {
                "size": 10
            }
        }
    }
    """)
    print('生成图谱完成')
    return net.generate_html()

#链接嵌入测试
def generate_quadruple_graph_html_with_link(folder_paths, height="1000px"):
    net = Network(height=height, width="100%", directed=True, notebook=False, cdn_resources='in_line')
    net.barnes_hut()
    added_nodes = set()
    added_edges = set()
    ent1_to_url = {}

    all_quadruples = []

    # 第一次遍历：提取所有四元组和ent1链接映射
    for folder_path in folder_paths:
        if not os.path.isdir(folder_path):
            print(f"警告：路径 {folder_path} 不是有效的文件夹，已跳过。")
            continue

        for filename in os.listdir(folder_path):
            print("正在处理文件:", filename)
            if filename.endswith(".json"):
                filepath = os.path.join(folder_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    this_url = data.get('link')
                    quadruples = data.get("四元组", [])
                    for quad in quadruples:
                        ent1 = quad.get("实体1", "").strip()
                        event = quad.get("事件", "").strip()
                        ent2 = quad.get("实体2", "").strip()
                        sentiment = quad.get("情感", "").strip()

                        if not (ent1 and ent2 and event and sentiment):
                            continue

                        all_quadruples.append((ent1, event, ent2, sentiment))
                        if this_url:
                            ent1_to_url[ent1] = this_url  # 记录 ent1 的链接

    # 第二次遍历：绘制节点和边
    for ent1, event, ent2, sentiment in all_quadruples:
        # 节点颜色
        if "负面" in sentiment or "消极" in sentiment:
            ent2_color = "orange"
        elif "正面" in sentiment or "积极" in sentiment:
            ent2_color = "green"
        else:
            ent2_color = "lightblue"

        # 添加 ent1 节点
        if ent1 not in added_nodes:
            if ent1 in ent1_to_url:
                net.add_node(ent1, label=ent1, color="lightblue",
                             title=f"<a href='{ent1_to_url[ent1]}' target='_blank'>{ent1}</a>")
            else:
                net.add_node(ent1, label=ent1, color="lightblue")
            added_nodes.add(ent1)

        # 添加 ent2 节点
        if ent2 not in added_nodes:
            net.add_node(ent2, label=ent2, color=ent2_color)
            added_nodes.add(ent2)

        # 添加边
        edge_id = (ent1, ent2, event, sentiment)
        if edge_id not in added_edges:
            edge_label = f"{event} + {sentiment}"
            net.add_edge(ent1, ent2, label=edge_label)
            added_edges.add(edge_id)

    # 图谱样式
    net.set_options("""
    var options = {
        "nodes": {
            "font": {
                "size": 13
            }
        },
        "edges": {
            "font": {
                "size": 10
            }
        }
    }
    """)

    # 生成 HTML
    html = net.generate_html()

    # 构造 JavaScript 映射字典
    js_url_mapping = ",\n        ".join(
        [f'"{ent}": "{url}"' for ent, url in ent1_to_url.items()]
    )

    js_script = f"""
    <script type="text/javascript">
        var urls = {{
            {js_url_mapping}
        }};
        network.on("click", function(params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                if (urls[nodeId]) {{
                    window.open(urls[nodeId], "_blank");
                }}
            }}
        }});
    </script>
    """

    # 插入脚本到 HTML 中
    html = html.replace("</body>", js_script + "\n</body>")

    print('生成图谱完成')
    return html



if __name__ == "__main__":
    pass
    # 调用函数，生成图谱
    # 你可以在这里指定文件夹路径和输出文件名
    # draw_quadruple_graph_from_folder("news_json", "quadruple_graph.html")
    # 直接使用默认参数 
    
    # folders=['./json_file']
    # html=generate_quadruple_graph_html_with_link(folders)
    # with open("graph.html", "w", encoding="utf-8") as f:
    #     f.write(html)
