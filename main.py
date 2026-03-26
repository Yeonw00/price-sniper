import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()


def get_danawa_lowest_price(model_name):
    # 다나와 검색 URL
    url = "https://search.danawa.com/dsearch.php"
    params = {"query": model_name}

    # 봇 차단 방지를 위한 User-Agent 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"[{model_name}] 검색 결과를 가져오는 중...")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # 주의: 다나와 웹페이지 구조에 따라 아래 선택자는 언제든 수정이 필요할 수 있습니다.
    # 크롬 개발자 도구로 실제 첫 번째 상품 가격이 있는 태그를 확인하세요.
    price_elements = soup.select(".price_sect strong")

    if price_elements:
        price_list = []

        for element in price_elements:
            raw_text = element.text.strip()
            try:
                price_part = raw_text.split("원")[0]
                price = int(price_part.replace(",", "").strip())

                if price > 100000:
                    price_list.append(price)
            except ValueError:
                continue

        if price_list:
            lowest_price = min(price_list)
            print(f"수집된 전체 가격들: {price_list}")
            return lowest_price
        else:
            print("조건에 맞는 유효한 가격을 찾지 못했습니다.")
            return None

    else:
        print("해당 선택자로 요소를 찾지 못했습니다.")
        return None


def send_email_alert(subject, body, to_email):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    if not sender_email or not sender_password:
        print(".env 파일에 이메일 계정 정보가 없습니다!")
        return None

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email
    msg.set_content(body)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # TLS 보안 연결
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("성공적으로 이메일 알림을 보냈습니다!")
    except Exception as e:
        print(f"이메일 발송 실패: {e}")


def main():
    # 설정값
    target_model = "MFHP4KH/A"  # 검색할 모델명
    target_price = 289000  # 알림을 받을 기준 가격 (예: 28만 원)
    my_email = os.getenv("RECEIVER_EMAIL")

    current_price = get_danawa_lowest_price(target_model)

    if current_price:
        print(f"현재 최저가: {current_price:,}원")

        # 현재 가격이 목표 가격보다 작거나 같으면 메일 발송
        if current_price <= target_price:
            subject = f"🔔 [최저가 알림] {target_model} 가격 하락!"
            body = f"기다리시던 {target_model}의 현재 최저가가 {current_price:,}원으로 떨어졌습니다.\n목표가: {target_price:,}원"
            send_email_alert(subject, body, my_email)
        else:
            print("아직 설정한 목표 가격까지 떨어지지 않았습니다.")
    else:
        print("가격을 파싱하지 못했습니다. HTML 구조나 CSS 선택자를 확인해 주세요.")


if __name__ == "__main__":
    main()
