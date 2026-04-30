import requests
import time
import re
from typing import Optional, List, Dict
from email.utils import parsedate_to_datetime

class MicrosoftClient:
    def __init__(self, api_key: str):
        self.base_url = "https://firstmail.ltd/api/v1"
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "accept": "application/json"
        }

    def get_inbox(self, email: str, password: str) -> List[Dict]:
        if not password:
            print("Ошибка: для Firstmail требуется пароль")
            return []

        try:
            payload = {
                "email": email,
                "password": password,
                "limit": 50,
                "folder": "INBOX"
            }
            response = requests.post(
                f"{self.base_url}/email/messages",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('messages'):
                    return data['data']['messages']
            elif response.status_code == 401:
                print("❌ Неверный логин или пароль")
            else:
                print(f"❌ Ошибка HTTP {response.status_code}: {response.text[:200]}")
            return []
        except Exception as e:
            print(f"❌ Ошибка получения списка писем: {e}")
            return []

    @staticmethod
    def _get_message_timestamp(message: Dict) -> int:
        """
        Извлекает timestamp из сообщения: сначала пробует числовое поле 'timestamp',
        затем парсит строку 'date' (RFC 2822), возвращает 0, если ничего не подошло.
        """
        ts = message.get('timestamp')
        if ts and isinstance(ts, (int, float)):
            return int(ts)
        date_str = message.get('date')
        if date_str:
            try:
                # Парсим строку типа "Fri, 30 Apr 2026 09:52:00 GMT"
                dt = parsedate_to_datetime(date_str)
                return int(dt.timestamp())
            except Exception:
                pass
        return 0

    def find_microsoft_code(self, email: str, password: str, attempts: int = 2, interval_first: int = 7, interval_second: int = 8) -> Optional[str]:
        intervals = [interval_first, interval_second]

        for attempt in range(1, attempts + 1):
            print(f"[Попытка {attempt}/{attempts}] Проверяю почту {email}...")
            messages = self.get_inbox(email, password)
            if not messages:
                print("⚠️ Нет писем или ошибка получения")
                continue

            # Сортировка по убыванию даты (новые первыми)
            messages.sort(key=self._get_message_timestamp, reverse=True)

            print(f"📬 Получено {len(messages)} писем (отсортированы по дате)")
            for idx, msg in enumerate(messages):
                print(f"   Письмо {idx+1}: date={msg.get('date')}, from={msg.get('from')[:50]}")

            for message in messages:
                sender = message.get('from', '').lower()
                if 'accountprotection.microsoft.com' not in sender:
                    continue

                print(f"📧 Найдено письмо от Microsoft. Отправитель: {sender[:80]}")
                body_html = message.get('body_html', '')
                body_text = message.get('body_text', '')
                content = body_html or body_text

                code = self._extract_code_with_keywords(content)
                if not code:
                    code = self._extract_any_six_digits(content)

                if code:
                    print(f"✅ Код найден в письме от {message.get('date')}: {code}")
                    return code
                else:
                    print("⚠️ Код не найден в этом письме, проверяем следующее...")

            if attempt < attempts:
                wait_time = intervals[attempt - 1]
                print(f"⏳ Следующая проверка через {wait_time} сек...")
                time.sleep(wait_time)

        print(f"❌ Код не обнаружен после {attempts} попыток")
        return None

    def _extract_code_with_keywords(self, content: str) -> Optional[str]:
        if not content:
            return None

        patterns = [
            r'Codice\s+di\s+sicurezza\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
            r'codice\s+di\s+sicurezza\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
            r'security\s+code\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
            r'verification\s+code\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
            r'código\s+de\s+seguridad\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
            r'code\s+de\s+sécurité\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
            r'Bestätigungscode\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
            r'Код\s+безопасности\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
            r'код\s+безопасности\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
            r'код\s+подтверждения\s*:\s*(?:<[^>]*>)*\s*(\d{6})',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _extract_any_six_digits(content: str) -> Optional[str]:
        matches = re.finditer(r'\d{6}', content)
        for match in matches:
            start = match.start()
            if start > 0 and content[start - 1] == '#':
                continue
            return match.group()
        return None