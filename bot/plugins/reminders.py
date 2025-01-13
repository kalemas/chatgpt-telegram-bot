import logging
from typing import Dict, Any
from .plugin import Plugin
from datetime import datetime
import json
import os

class RemindersPlugin(Plugin):
    """
    Плагин для управления напоминаниями и интеграциями
    """
    def __init__(self):
        self.reminders = {}
        self.reminders_file = os.path.join(os.path.dirname(__file__), "reminders.json")
        self.load_reminders()

    def get_source_name(self) -> str:
        return "Reminders"

    def get_spec(self) -> [Dict]:
        return [{
            "name": "set_reminder",
            "description": f'Установить напоминание на определенное время, сейчас {datetime.now().strftime("%Y%m%d%H%M%S")}',
            "parameters": {
                "type": "object",
                "properties": {
                    "time": {
                        "type": "string",
                        "description": "Время напоминания в формате YYYY-MM-DD HH:MM"
                    },
                    "message": {
                        "type": "string",
                        "description": "Текст напоминания"
                    },
                    "current_time": {
                        "type": "string",
                        "description": f'Текущее время {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                    },
                    "integration": {
                        "type": "string", 
                        "description": "Интеграция для отправки (telegram)",
                        "enum": ["telegram",]
                    }
                },
                "required": ["time", "message", "integration","current_time"]
            }
        },
        {
            "name": "list_reminders",
            "description": "Показать список активных напоминаний",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "delete_reminder", 
            "description": "Удалить напоминание по ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {
                        "type": "string",
                        "description": "ID напоминания для удаления"
                    }
                },
                "required": ["reminder_id"]
            }
        }]

    def load_reminders(self):
        """Load reminders from storage"""
        try:
            if os.path.exists(self.reminders_file):  # Fixed: using reminders_file instead of storage_path
                with open(self.reminders_file, 'r') as f:  # Fixed: using reminders_file
                    self.reminders = json.load(f) 
                    if not isinstance(self.reminders, dict):  # Ensure it's a dictionary
                        self.reminders = {}
        except Exception as e:
            logging.error(f"Error loading reminders: {e}")
            self.reminders = {}  # Initialize as empty dict, not list

    def save_reminders(self):
        """Save reminders to storage"""
        try:
            with open(self.reminders_file, 'w') as f:  # Fixed: using reminders_file
                json.dump(self.reminders, f, ensure_ascii = False)
        except Exception as e:
            logging.error(f"Error saving reminders: {e}")

    async def check_reminders(self, helper):
        """
        Проверка и отправка напоминаний
        """
        current_time = datetime.now()
        self.load_reminders()

        for user_id, user_reminders in list(self.reminders.items()):
            for reminder_id, reminder in list(user_reminders.items()):
                # Convert reminder time from ISO format string to datetime
                reminder_time = datetime.fromisoformat(reminder['time'])
                
                # Check if reminder time is in the past
                if current_time >= reminder_time:
                    await self.send_reminder(reminder, helper)
                    del self.reminders[user_id][reminder_id]
                    
                    # Remove user dict if no reminders left
                    if not self.reminders[user_id]:
                        del self.reminders[user_id]
        
        # Save changes if any reminders were processed
        self.save_reminders()

    async def send_reminder(self, reminder: Dict, helper) -> None:
        """
        Отправка напоминания через выбранную интеграцию
        """
        if reminder["integration"] == "telegram":
            await helper.send_message(
                chat_id=reminder["user_id"],
                text=f"🔔 Напоминание:\n{reminder['message']}",
                reply_to_message_id=reminder.get("reply_to_message_id")
            )
        # Здесь можно добавить другие интеграции (email, slack)

    async def execute(self, function_name: str, helper, **kwargs) -> Dict:
        """
        Выполнение функций плагина
        """
        if function_name == "set_reminder":
            user_id = str(helper.user_id)
            reminder_id = f'{datetime.now().strftime("%Y%m%d%H%M%S")}_{user_id}'
            # Convert datetime to ISO format string
            reminder_time = datetime.strptime(kwargs["time"], "%Y-%m-%d %H:%M")
            
            reminder = {
                "id": reminder_id,
                "user_id": user_id,
                "time": reminder_time.isoformat(),
                "message": kwargs["message"],
                "integration": kwargs["integration"],
                "reply_to_message_id": helper.message_id
            }

            if user_id not in self.reminders:
                self.reminders[user_id] = {}
            self.reminders[user_id][reminder_id] = reminder
            self.save_reminders()
            
            return {
                "success": True,
                "message": f"Напоминание установлено на {kwargs['time']}"
            }

        elif function_name == "list_reminders":
            user_id = str(helper.user_id)
            user_reminders = self.reminders.get(user_id, {})
            
            if not user_reminders:
                return {"message": "У вас нет активных напоминаний"}
            
            reminders_list = []
            for r_id, r in user_reminders.items():
                reminders_list.append(f"ID: {r_id}\nВремя: {r['time']}\nСообщение: {r['message']}")
            
            return {
                "message": "Ваши напоминания:\n\n" + "\n\n".join(reminders_list)
            }

        elif function_name == "delete_reminder":
            user_id = str(helper.user_id)
            reminder_id = kwargs["reminder_id"]
            
            if user_id in self.reminders and reminder_id in self.reminders[user_id]:
                del self.reminders[user_id][reminder_id]
                if not self.reminders[user_id]:
                    del self.reminders[user_id]
                self.save_reminders()
                return {"message": f"Напоминание {reminder_id} удалено"}
            
            return {"message": "Напоминание не найдено"}

        return {"error": "Unknown function"}