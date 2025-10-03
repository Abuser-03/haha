def check_document_name_match(self, text_results, found_codes):
    """Проверяет соответствие кода и наименования"""
    # Словарь соответствий код → наименование
    code_to_name = {
        'СБ': 'сборочный чертёж',
        'Э5': 'схема электрическая подключения',
        'Э3': 'схема электрическая принципиальная',
        # ... добавьте все из таблицы
    }

    errors = []
    for code_info in found_codes:
        code = code_info['code']
        expected_name = code_to_name.get(code, '').lower()

        # Ищем наименование в тексте
        full_text = ' '.join([r['text'].lower() for r in text_results])

        if expected_name and expected_name not in full_text:
            errors.append({
                'type': 'code_name_mismatch',
                'code': code,
                'expected': expected_name,
                'found_text': full_text[:100]
            })

    return errors