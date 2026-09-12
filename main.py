import hashlib
import hmac
import os
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Твої тестові дані мерчанта від WayForPay (для розробки)
MERCHANT_ACCOUNT = 'test_merch_noclient'
MERCHANT_SECRET_KEY = (
    'flk3409refn54t54t*FNJRET'  # Стандартний тестовий ключ WayForPay
)


def generate_signature(params_list, secret_key):
  """Генерує криптографічний підпис для безпеки платежу"""
  string_to_sign = ';'.join(str(param) for param in params_list)
  signature = hmac.new(
      secret_key.encode('utf-8'),
      string_to_sign.encode('utf-8'),
      hashlib.md5,
  ).hexdigest()
  return signature


@app.route('/')
def index():
  # Рендеримо головну сторінку з кнопкою оплати
  return render_template('index.html')


@app.route('/create-payment', methods=['POST'])
def create_payment():
  """Ендпоінт, який готує безпечні дані для віджета на фронтенді"""

  # Дані замовлення (у реальному проєкті вони беруться з кошика користувача)
  order_reference = 'ORDER-101'
  order_date = 1726156800  # Приклад таймстампа (у реалі використовуй поточний час)
  amount = '100.00'
  currency = 'UAH'
  product_name = 'Тестовий товар'
  product_price = '100.00'
  product_count = '1'

  # Порядок параметрів суворо визначений документацією WayForPay для підпису
  sign_params = [
      MERCHANT_ACCOUNT,
      'mysite.com',  # merchantDomainName
      order_reference,
      str(order_date),
      amount,
      currency,
      product_name,
      product_count,
      product_price,
  ]

  # Генеруємо підпис на сервері (секретний ключ ніколи не потрапляє на фронтенд!)
  merchant_signature = generate_signature(sign_params, MERCHANT_SECRET_KEY)

  # Повертаємо всі необхідні дані у форматі JSON на нашу HTML-сторінку
  return jsonify({
      'merchantAccount': MERCHANT_ACCOUNT,
      'merchantDomainName': 'mysite.com',
      'orderReference': order_reference,
      'orderDate': order_date,
      'amount': amount,
      'currency': currency,
      'productName': [product_name],
      'productPrice': [product_price],
      'productCount': [product_count],
      'merchantSignature': merchant_signature,
      'language': 'UA',
  })


@app.route('/webhook', methods=['POST'])
def payment_webhook():
  """Вебхук — сюди платіжна система надсилає POST-запит у фоновому режимі,

  коли гроші успішно списалися. Навіть якщо користувач закрив браузер, цей код
  спрацює і зафіксує оплату в базі даних.
  """
  data = request.json
  print('Отримано вебхук від платіжної системи:', data)

  if data and data.get('transactionStatus') == 'Approved':
    order_id = data.get('orderReference')
    print(f'Замовлення {order_id} успішно оплачено! Надаємо товар клієнту.')

    # Тут треба сформувати відповідь для WayForPay, що ми все отримали
    # (WayForPay вимагає підтвердження у вигляді певного JSON)
    time_received = data.get('time')
    response_string = f'{order_id};accept;{time_received}'
    response_sign = hmac.new(
        MERCHANT_SECRET_KEY.encode('utf-8'),
        response_string.encode('utf-8'),
        hashlib.md5,
    ).hexdigest()

    return jsonify({
        'orderReference': order_id,
        'status': 'accept',
        'time': time_received,
        'signature': response_sign,
    })

  return jsonify({'status': 'error'})


if __name__ == '__main__':
  # Динамічний порт для Render + fallback на 5000 для локального запуску
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)