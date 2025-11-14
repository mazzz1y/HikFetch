def check_basic_auth(username, password, credentials):
    web_user = credentials.get('web_username')
    web_pass = credentials.get('web_password')
    if not web_user or not web_pass:
        return True
    return username == web_user and password == web_pass
