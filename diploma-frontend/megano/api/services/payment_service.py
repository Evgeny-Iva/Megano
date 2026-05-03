
class PaymentService:
    @staticmethod
    def validate_card_data(data):
        """Валидация данных карты"""
        errors = {}

        number = data.get('number', '').replace(' ', '').replace('-', '')
        if not number.isdigit() or len(number) != 16:
            errors['number'] = 'Номер карты должен содержать 16 цифр'

        name = data.get('name', '')
        if len(name.strip()) < 3:
            errors['name'] = 'Введите имя владельца карты'

        month = data.get('month', '')
        if not month.isdigit() or int(month) < 1 or int(month) > 12:
            errors['month'] = 'Месяц должен быть от 01 до 12'

        year = data.get('year', '')
        if not year.isdigit() or len(year) != 2:
            errors['year'] = 'Год должен содержать 2 цифры'
        else:
            year_num = 2000 + int(year)
            if year_num < datetime.now().year:
                errors['year'] = 'Срок действия карты истек'

        code = data.get('code', '')
        if not code.isdigit() or len(code) != 3:
            errors['code'] = 'CVV код должен содержать 3 цифры'

        if errors:
            raise ValidationError(errors)

        return data

    @staticmethod
    def process_payment(order, card_data):
        """Обработка оплаты"""
        order.status = 'paid'
        order.save()
        return order