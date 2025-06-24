import os
from flask import Flask, render_template, request
from notion_client import Client
from openai import OpenAI
from dotenv import load_dotenv

# --- 1. 加载环境变量 ---
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAGE_ID = os.getenv("PAGE_ID")
BACKUP_PAGE_ID = os.getenv("BACKUP_PAGE_ID") # 新增：读取备份页面ID

# 启动时检查所有必需的配置是否存在
if not all([NOTION_TOKEN, OPENAI_API_KEY, PAGE_ID, BACKUP_PAGE_ID]):
    raise ValueError("错误：请确保 .env 文件存在，并且其中包含了 NOTION_TOKEN, OPENAI_API_KEY, PAGE_ID, 和 BACKUP_PAGE_ID。")

# --- 2. 初始化客户端 (不变) ---
app = Flask(__name__)
try:
    notion = Client(auth=NOTION_TOKEN)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    app.logger.error(f"客户端初始化失败: {e}")

# --- 3. 核心功能函数 (所有函数都可重用，无需修改) ---

def get_page_content(page_id: str) -> str:
    # ... (此函数代码不变)
    try:
        response = notion.blocks.children.list(block_id=page_id)
        content = ["".join([t["plain_text"] for t in block["paragraph"]["rich_text"]])
                   for block in response.get("results", []) if block["type"] == "paragraph"]
        return "\n".join(content)
    except Exception as e:
        app.logger.error(f"读取Notion页面内容失败 (ID: {page_id}): {e}")
        raise

def update_notion_page(page_id: str, new_content: str):
    # ... (此函数代码不变, 它可以清空并写入任何页面)
    try:
        old_blocks = notion.blocks.children.list(block_id=page_id)["results"]
        for block in old_blocks:
            notion.blocks.delete(block_id=block["id"])
        new_blocks = [{"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": p}}]}}
                      for p in new_content.split('\n') if p]
        for i in range(0, len(new_blocks), 100):
            notion.blocks.children.append(block_id=page_id, children=new_blocks[i:i + 100])
    except Exception as e:
        app.logger.error(f"更新Notion页面失败 (ID: {page_id}): {e}")
        raise

def get_chatgpt_answer(context: str, question: str) -> str:
    # ... (此函数代码不变)
    SYSTEM_PROMPT = "你是一个精准的文档问答助理..."
    user_prompt = f"这是原始文档内容...\n{context}\n...\n这是我的问题...\n{question}\n..."
    # ... (try/except block as before)
    try:
        response = openai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}])
        return response.choices[0].message.content.strip()
    except Exception as e:
        app.logger.error(f"调用OpenAI API进行查询失败: {e}")
        raise

def get_chatgpt_merge(original_content: str, new_content: str) -> str:
    # ... (此函数代码不变)
    SYSTEM_PROMPT = "你是一个文档助理..."
    user_prompt = f"这是原始文档内容...\n{original_content}\n...\n这是新的指令...\n{new_content}\n..."
    # ... (try/except block as before)
    try:
        response = openai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}])
        return response.choices[0].message.content.strip()
    except Exception as e:
        app.logger.error(f"调用OpenAI API进行合并失败: {e}")
        raise


# --- 4. Flask路由 (新增对 backup 动作的处理) ---

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_request():
    message = ""
    answer = ""
    try:
        action = request.form.get('action')
        user_input = request.form.get('user_input', '') # 备份时输入框内容可为空

        app.logger.info(f"收到请求，动作为: {action}")

        # 新增：备份逻辑分支
        if action == 'backup':
            app.logger.info(f"正在从主文档 (ID: {PAGE_ID}) 备份到 (ID: {BACKUP_PAGE_ID})")
            # 1. 读取主文档内容
            content_to_backup = get_page_content(PAGE_ID)
            # 2. 将内容写入备份文档 (update_notion_page 完美适用于此)
            update_notion_page(BACKUP_PAGE_ID, content_to_backup)
            message = "✅ 备份成功！内容已完整复制到您的备份文档。"

        elif action == 'update':
            if not user_input:
                message = "错误：更新文档时，输入内容不能为空！"
                return render_template('index.html', message=message)
            original_content = get_page_content(PAGE_ID)
            final_content = get_chatgpt_merge(original_content, user_input)
            update_notion_page(PAGE_ID, final_content)
            message = "✅ Notion文档更新成功！"

        elif action == 'query':
            if not user_input:
                message = "错误：查询时，问题内容不能为空！"
                return render_template('index.html', message=message)
            original_content = get_page_content(PAGE_ID)
            answer = get_chatgpt_answer(original_content, user_input)
            message = "✅ 查询成功！"
            
        else:
            message = "错误：未知的操作。"

    except Exception as e:
        message = f"❌ 操作过程中发生错误: {e}"
        app.logger.error(f"处理流程失败: {e}")

    return render_template('index.html', message=message, answer=answer)


# --- 5. 启动Web应用 (不变) ---
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)