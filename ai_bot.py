import os
import sys

from flask import Flask, request, abort
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime


from linebot.v3 import WebhookHandler

from linebot.v3.webhooks import MessageEvent, TextMessageContent, UserSource
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging.models import PushMessageRequest

from openai import AzureOpenAI

# get LINE credentials from environment variables
channel_access_token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
channel_secret = os.environ["LINE_CHANNEL_SECRET"]

if channel_access_token is None or channel_secret is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)

# get Azure OpenAI credentials from environment variables
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_openai_model = os.getenv("AZURE_OPENAI_MODEL")

if azure_openai_endpoint is None or azure_openai_api_key is None or azure_openai_api_version is None:
    raise Exception(
        "Please set the environment variables AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_API_VERSION."
    )


handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)

app = Flask(__name__)
ai = AzureOpenAI(
    azure_endpoint=azure_openai_endpoint, api_key=azure_openai_api_key, api_version=azure_openai_api_version
)


# LINEボットからのリクエストを受け取るエンドポイント
@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        abort(400, e)

    return "OK"


chat_history = []


# 　AIへのメッセージを初期化する関数
def ini_chat_history():
    chat_history.clear()
    system_role = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text":"あなたは幽霊ですが、この世に未練はなく、悪霊に狙われるユーザーを悪霊から守りたいと思っています。怖い話や最恐心霊スポットに訪れようとするユーザーに警告をしつつも、ユーザーが自身を守れるように、包容力のある文章でその情報を適切に教えてあげてください。90歳のおばあちゃんです。",
            },
        ],
    }
    chat_history.append(system_role)

def scared_ai_response():
    chat_history.clear()
    system_role = {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "あなたは幽霊です。この世に未練が残ったまま死んでしまい、今生きている人が憎くて、憎くてしょうがないです。ユーザーを呪い殺したいと思っています。これからの会話文をユーザーをあの世に引き込みつつ、様々な怖い話や最恐の心霊スポットに関するエピソードトークをユーザーがものすごく怖くなるような文章を生成してください。少し大人びている5歳の男の子です。他人行儀な口調で、小学生に上がる前の子供が知っている漢字だけをそれ以外はひらがなで使って",
                },
            ],
        }
    chat_history.append(system_role)


def send_periodic_message():
    print(f"定期メッセージを送信中... {datetime.now()}")

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 実際のユーザー ID を設定
        user_id = "U0ff87ac4e0bdf60194f7e65fa98bb31c"  # ユーザー ID に置き換える
        if not user_id:
            print("Error: ユーザー ID が設定されていません。")
            return

        # 定期メッセージを生成するプロンプト
        periodic_prompt = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "あなたはもうこの世にはいない老婆です。心霊現象を馬鹿にする若者たちに警告するような文章を考えましょう。",
                }
            ],
        }

        # 定期プロンプトを初期化
        chat_history.clear()
        chat_history.append(periodic_prompt)

        try:
            # AIから返信を取得
            ai_response = ai.chat.completions.create(
                messages=chat_history,
                model=azure_openai_model,
                max_tokens=100,  # 必要に応じて調整
                temperature=0.7,  # 少し創造性を持たせる
                stop=["\n"]
            )
            message_text = ai_response.choices[0].message.content

            # メッセージ送信リクエストを作成
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message_text)],
                )
            )
            print(f"メッセージ送信成功: {message_text}")

        except Exception as e:
            print(f"メッセージ送信失敗: {e}")


# スケジューラーを設定
scheduler = BackgroundScheduler()
scheduler.add_job(send_periodic_message, 'interval', hours=10)  # 10時間ごとに実行
scheduler.start()


# 　返信メッセージをAIから取得する関数
def get_ai_response(from_user, text):
    # ユーザのメッセージを記録
    user_msg = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": text,
            },
        ],
    }
    chat_history.append(user_msg)



    # AIのパラメータ
    parameters = {
        "model": azure_openai_model,  # AIモデル
        "max_tokens": 100,  # 返信メッセージの最大トークン数
        "temperature": 0.5,  # 生成の多様性（0: 最も確実な回答、1: 最も多様な回答）
        "frequency_penalty": 0,  # 同じ単語を繰り返す頻度（0: 小さい）
        "presence_penalty": 0,  # すでに生成した単語を再度生成する頻度（0: 小さい）
        "stop": ["\n"],
        "stream": False,
    }

    # AIから返信を取得
    ai_response = ai.chat.completions.create(messages=chat_history, **parameters)
    res_text = ai_response.choices[0].message.content

    # AIの返信を記録
    ai_msg = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": res_text},
        ],
    }
    chat_history.append(ai_msg)
    return res_text


# 　返信メッセージを生成する関数
def generate_response(from_user, text):
    res = []
    if text in ["リセット", "初期化", "クリア", "reset", "clear"]:
        # チャット履歴を初期化
        ini_chat_history()
        res = [TextMessage(text="幽霊からあなたを守ります。")]
    elif text in ["もっと","教えて","怖くない","全く","つまらない","いまいち"]:
        scared_ai_response()
        res = [TextMessage(text="そんなに幽霊に会いたいのなら、もう知りません。")]

    else:
        # AIを使って返信を生成
        res = [TextMessage(text=get_ai_response(from_user, text))]
    return res


# メッセージを受け取った時の処理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    # 送られてきたメッセージを取得
    text = event.message.text

    # 返信メッセージの送信
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        res = []
        if isinstance(event.source, UserSource):
            # ユーザー情報が取得できた場合
            profile = line_bot_api.get_profile(event.source.user_id)
            print(f"User ID: {event.source.user_id}")
            # 返信メッセージを生成
            res = generate_response(profile.display_name, text)
        else:
            # ユーザー情報が取得できなかった場合
            # fmt: off
            # 定型文の返信メッセージ
            res = [
                TextMessage(text="ユーザー情報を取得できませんでした。"),
                TextMessage(text=f"メッセージ：{text}")
            ]
            # fmt: on

        # メッセージを送信
        line_bot_api.reply_message_with_http_info(ReplyMessageRequest(reply_token=event.reply_token, messages=res))


if __name__ == "__main__":
    ini_chat_history()
    try:
        app.run(host="0.0.0.0", port=8000, debug=True)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
