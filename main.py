from flask import Flask, render_template, request, session, redirect, Response, jsonify
import _theb as theb
import _forefront as ff
import json
import _you as you
from typing import Any
from datetime import datetime, timedelta
from urllib.parse import quote as urlparse
from json.decoder import JSONDecodeError
import requests
import poe
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
poe.logger.setLevel(logging.INFO)
import time

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"


def get_time():
    return round(datetime.now().timestamp())


def datetime_to_relative(time):
    x = str(timedelta(seconds=round(datetime.now().timestamp() - time))).split(":")
    return x[0] + " hours, " + x[1] + " minutes ago"


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/gpt4_forefornt")
def gpt4page():
    with open("db.json") as f:
        db = json.load(f)

    accs = db["accounts"]

    final = []

    for i, v in enumerate(accs):
        # pos,last_used_relative_time,
        final.append((i + 1, datetime_to_relative(v["last_timestamp"])))

    return render_template("gpt4page.html", acc=final)


@app.route("/gpt4_you")
def gpt4page_you():
    with open("db_you.json") as f:
        data = json.load(f)

    data["gpt4youchat"] = []

    with open("db_you.json", "w") as f:
        f.write(json.dumps(data, indent=4))

    return render_template("gpt4page_you.html")


@app.route("/converse/gpt4_you", methods=["POST"])
def gpt4_you():
    x = request.get_data().decode("utf-8")
    data = json.loads(x)
    # data = request.get_json()
    prompt = data["prompt"]

    with open("db_you.json") as f:
        db = json.load(f)

    chat = db["gpt4youchat"]

    response = you.Completion.create(
        prompt=prompt, chat=chat, include_links=True, detailed=True, debug=False
    )

    db["gpt4youchat"].append({"question": prompt, "answer": response.text})

    with open("db_you.json", "w") as f:
        f.write(json.dumps(db, indent=4))

    return jsonify({"response": str(response.text)})


@app.route("/gpt3")
def gpt3page():
    return render_template("gpt3page.html")


@app.route("/converse/gpt3", methods=["POST"])
def gpt3():
    x = request.get_data().decode("utf-8")
    data = json.loads(x)
    # data = request.get_json()
    prompt = data["prompt"]

    gpt3Comp = theb.Completion

    def stream_resp():
        for token in gpt3Comp.create(prompt):
            yield token
        # print(gpt3Comp.last_msg_id)

    return app.response_class(stream_resp(), mimetype="text/event-stream")


@app.route("/converse/gpt4_forefront", methods=["POST"])
def gpt4():
    x = request.get_data().decode("utf-8")
    data = json.loads(x)
    print(data)
    # data = request.get_json()
    prompt = data["prompt"]
    make_new = data["make_new"]
    try:
        account_num_to_use = int(data["account_num"])
    except ValueError:

        def x():
            yield "Account number must be an integer ...."

        return app.response_class(x(), mimetype="text/event-stream")

    with open("db.json") as f:
        db = json.load(f)

    if len(db["accounts"]) == 0:
        try:
            email = ff.Email()
            res: Any = email.CreateAccount()
            db["accounts"].append(
                {"client": res.client, "sessionID": res.sessionID, "last_timestamp": 0}
            )
            with open("db.json", "w") as f:
                f.write(json.dumps(db, indent=4))

            def x():
                yield "Successfully created account!\nRefresh to see it in accounts section"

            return app.response_class(x(), mimetype="text/event-stream")
        except Exception as e:
            print(e)

            def x():
                yield "Unable to create account, retrying might help"

            return app.response_class(x(), mimetype="text/event-stream")

    if make_new:
        try:
            print("MAKING A ACCOUNT")
            email = ff.Email()
            res: Any = email.CreateAccount()
            db["accounts"].append(
                {"client": res.client, "sessionID": res.sessionID, "last_timestamp": 0}
            )

            with open("db.json", "w") as f:
                f.write(json.dumps(db, indent=4))

            def x():
                yield "Successfully created account!\nRefresh to see it in accounts section"

            return app.response_class(x(), mimetype="text/event-stream")
        except Exception as e:
            print(e)

            def x():
                yield "Unable to create account, retrying might help"

            return app.response_class(x(), mimetype="text/event-stream")

    with open("db.json") as f:
        db = json.load(f)

    if account_num_to_use > len(db["accounts"]):

        def x():
            yield f'Account out of range!!!. Max account number = {len(db["accounts"])}'

        return app.response_class(x(), mimetype="text/event-stream")

    res: Any = db["accounts"][account_num_to_use - 1]
    print(res)
    client = res["client"]
    sessionID = res["sessionID"]
    # try:
    forefront = ff.Model(
        sessionID=sessionID,
        client=client,
        model="gpt-4",
        conversationID=db["accounts"][account_num_to_use - 1].get("convo_id", None),
    )
    forefront.SetupConversation(prompt)
    # except Exception as e:
    #     print(e)
    #     def err():
    #         content_sent=False
    #         yield f'ENDENDENDENDENDREASONREASONABRAKA {content_sent}'

    #     return app.response_class(err(),mimetype='text/event-stream')

    def stream_resp():
        content_sent = False
        # print(2)
        for r in forefront.SendConversation():
            # print(r)
            content_sent = True
            yield r.choices[0].delta.content.encode()

        # for i in range(100):
        #     content_sent = True
        #     yield f"{i}\n"
        #     time.sleep(1)

        yield f"ENDENDENDENDENDREASONREASONABRAKA {content_sent}"

    db["accounts"][account_num_to_use - 1].update({"last_timestamp": get_time()})
    db["accounts"][account_num_to_use - 1].update(
        {"convo_id": forefront.CONVERSATION_ID}
    )
    with open("db.json", "w") as f:
        f.write(json.dumps(db, indent=4))
    return app.response_class(stream_resp(), mimetype="text/event-stream")


@app.route("/gpt4_phind")
def gpt4page_phind():
    return render_template("gpt4page_phind.html")


@app.route('/utils/gpt4_phind_search',methods=['POST'])
def phind_search_ls():
    import _phind as ph
    x = request.get_data().decode("utf-8")
    data = json.loads(x)
    # data = request.get_json()
    prompt = data["prompt"]

    try:    
        search_resu,got_re = ph.Search().create(prompt, actualSearch = True),True
    except JSONDecodeError:
        print('Unable to get actual search results !!')
        search_resu,got_re = ph.Search().create(prompt, actualSearch = False),False
    sources_ls = []
    if got_re:
        sources_ls = search_resu['webPages']['value']

    return jsonify({'search_results':search_resu,'sources_ls':sources_ls,'gpt_res':got_re})


@app.route("/converse/gpt4_phind", methods=["POST"])
def gpt4_phind():
    import _phind as ph
    x = request.get_data().decode("utf-8")
    data = json.loads(x)
    # data = request.get_json()
    prompt = data["prompt"]
    search_results = data['search_results']
    
    def stream_resp():  
        content_sent = False
        for ress in ph.StreamingCompletion.create(
            model  = 'gpt-4',
            prompt = prompt,
            results     = search_results, 
            creative    = False,
            detailed    = True,
            codeContext = ''):

            content_sent = True
            yield ress.completion.choices[0].text

        yield f"ENDENDENDENDENDREASONREASONABRAKA {content_sent}"

    return app.response_class(stream_resp(), mimetype="text/event-stream")

@app.route('/gpt4_bard')
def gpt4page_bard():
    return render_template('gpt4page_bard.html')

@app.route('/converse/gpt4_bard',methods=['POST'])
def gpt4_bard():
    data = json.loads(request.get_data().decode("utf-8"))
    prompt = data["prompt"]

    url = f"https://gpt4free.crispypiez.repl.co/?prompt={urlparse(prompt,safe='')}&model=bard"

    headers = {
    'authority': 'gpt4free.crispypiez.repl.co',
    'Origin': 'gpt4free.crispypiez.repl.co',
    'Referer': 'gpt4free.crispypiez.repl.co',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
    }

    response = requests.get(url, headers=headers,verify=False)

    return jsonify({'response':response.content.decode()})


@app.route('/gpt4_poe')
def gpt4page_poe():
    return render_template('gpt4page_poe.html')

first_time_poe = True

@app.route('/converse/gpt4_poe',methods=['POST'])
def gpt4_poe():
    data = json.loads(request.get_data().decode("utf-8"))
    prompt = data["prompt"]
    with open('db_poe.json') as f:
        last_id = json.load(f)['last_idx']
    token = requests.get('https://gist.githubusercontent.com/jsmsj/03eb084a298eb5cc2abb0c573383fbfc/raw/7aef974ab67404a47eb7942524feee9d33c45c21/poe.txt').content.decode('utf-8').split('\n')[last_id]

    client = poe.Client(token)
    # #{'capybara': 'Sage', 'beaver': 'GPT-4', 'a2_2': 'Claude+', 'a2': 'Claude', 'chinchilla': 'ChatGPT', 'nutria': 'Dragonfly'}

    def stream_resp():  
        content_sent = False
        try:
            for chunk in client.send_message("beaver", prompt):
                content_sent = True
                yield chunk["text_new"]
        except RuntimeError as e:
            print(e)
            content_sent = True
            yield 'Daily limit reached for GPT4 with this account. switching the account.... Please resend your query'
            time.sleep(0.1)
            with open('db_poe.json','w') as f:
                f.write(json.dumps({'last_idx':last_id+1}))

        yield f"ENDENDENDENDENDREASONREASONABRAKA {content_sent}"

    return app.response_class(stream_resp(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
