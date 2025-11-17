from collections import UserDict
from datetime import datetime, date, timedelta
import pickle
from typing import Callable


FILE_NAME = "addressbook.pkl"


# ==========================
#       МОДЕЛІ ДАНИХ
# ==========================

class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    pass


class Phone(Field):
    """Телефон: рівно 10 цифр."""

    @staticmethod
    def _validate(value: str):
        if not (value.isdigit() and len(value) == 10):
            raise ValueError("Phone number must contain exactly 10 digits.")

    def __init__(self, value: str):
        self._validate(value)
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value: str):
        self._validate(new_value)
        self._value = new_value


class Birthday(Field):
    """Birthday у форматі DD.MM.YYYY."""

    def __init__(self, value: str):
        try:
            dt = datetime.strptime(value, "%d.%m.%Y").date()
            self._value = dt
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")

    @property
    def value(self) -> date:
        return self._value

    @value.setter
    def value(self, new_value: date):
        if not isinstance(new_value, date):
            raise ValueError("Birthday must be a date.")
        self._value = new_value

    def __str__(self):
        return self.value.strftime("%d.%m.%Y")


class Record:
    """Один контакт: ім'я, телефони, день народження."""

    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: list[Phone] = []
        self.birthday: Birthday | None = None

    def add_phone(self, phone: str):
        self.phones.append(Phone(phone))

    def find_phone(self, phone: str):
        for ph in self.phones:
            if ph.value == phone:
                return ph
        return None

    def remove_phone(self, phone: str):
        ph = self.find_phone(phone)
        if ph:
            self.phones.remove(ph)

    def edit_phone(self, old: str, new: str):
        ph = self.find_phone(old)
        if not ph:
            raise ValueError("Old phone number not found.")
        ph.value = new

    def add_birthday(self, bday: str):
        self.birthday = Birthday(bday)

    def __str__(self):
        phones = "; ".join(p.value for p in self.phones) if self.phones else "no phones"
        if self.birthday:
            return f"Contact name: {self.name.value}, phones: {phones}, birthday: {self.birthday}"
        return f"Contact name: {self.name.value}, phones: {phones}"


class AddressBook(UserDict):
    """Адресна книга."""

    def add_record(self, record: Record):
        self.data[record.name.value] = record

    def find(self, name: str):
        return self.data.get(name)

    def delete(self, name: str):
        if name in self.data:
            del self.data[name]

    def get_upcoming_birthdays(self) -> list:
        today = date.today()
        result = []

        for record in self.data.values():
            if not record.birthday:
                continue

            bday = record.birthday.value
            birthday_this_year = bday.replace(year=today.year)

            if birthday_this_year < today:
                birthday_this_year = birthday_this_year.replace(year=today.year + 1)

            diff = (birthday_this_year - today).days

            if 0 <= diff <= 7:
                congratulation_date = birthday_this_year

                # перенос на понеділок
                if congratulation_date.weekday() == 5:
                    congratulation_date += timedelta(days=2)
                if congratulation_date.weekday() == 6:
                    congratulation_date += timedelta(days=1)

                result.append({
                    "name": record.name.value,
                    "congratulation_date": congratulation_date.strftime("%Y.%m.%d")
                })

        return result


# ==========================
#  СЕРІАЛІЗАЦІЯ PICKLE
# ==========================

def save_data(book: AddressBook, filename=FILE_NAME):
    with open(filename, "wb") as f:
        pickle.dump(book, f)


def load_data(filename=FILE_NAME) -> AddressBook:
    try:
        with open(filename, "rb") as f:
            book = pickle.load(f)
            if not isinstance(book, AddressBook):
                return AddressBook()
            return book
    except FileNotFoundError:
        return AddressBook()
    except Exception:
        return AddressBook()


# ==========================
#   ДЕКОРАТОР ПОМИЛОК
# ==========================

def input_error(func: Callable):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, KeyError, IndexError) as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
    return wrapper


# ==========================
#     ХЕНДЛЕРИ КОМАНД
# ==========================

@input_error
def add_contact(args, book: AddressBook):
    name, phone = args[0], args[1]
    record = book.find(name)
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    else:
        message = "Contact updated."
    record.add_phone(phone)
    return message


@input_error
def change_contact(args, book: AddressBook):
    name, old_phone, new_phone = args[:3]
    record = book.find(name)
    if record is None:
        raise KeyError("Contact not found.")
    record.edit_phone(old_phone, new_phone)
    return "Phone changed."


@input_error
def show_phone(args, book: AddressBook):
    name = args[0]
    record = book.find(name)
    if not record:
        raise KeyError("Contact not found.")
    if not record.phones:
        return "No phones."
    return ", ".join(p.value for p in record.phones)


def show_all(book: AddressBook):
    if not book.data:
        return "No contacts."
    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args, book: AddressBook):
    name, bday = args[:2]
    record = book.find(name)
    if not record:
        raise KeyError("Contact not found.")
    record.add_birthday(bday)
    return "Birthday added."


@input_error
def show_birthday(args, book: AddressBook):
    name = args[0]
    record = book.find(name)
    if not record:
        raise KeyError("Contact not found.")
    if not record.birthday:
        return "No birthday set."
    return str(record.birthday)


@input_error
def birthdays(args, book: AddressBook):
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No birthdays next week."

    lines = []
    for item in upcoming:
        lines.append(f"{item['congratulation_date']}: {item['name']}")
    return "\n".join(lines)


# ==========================
#      ПАРСЕР КОМАНД
# ==========================

def parse_input(user_input: str):
    parts = user_input.split()
    if not parts:
        return "", []
    cmd = parts[0].lower()
    args = parts[1:]
    return cmd, args


# ==========================
#           MAIN
# ==========================

def main():
    book = load_data()
    print("Welcome to the assistant bot!")

    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ("exit", "close"):
            save_data(book)
            print("Good bye!")
            break

        elif command == "hello":
            print("How can I help you?")

        elif command == "add":
            print(add_contact(args, book))

        elif command == "change":
            print(change_contact(args, book))

        elif command == "phone":
            print(show_phone(args, book))

        elif command == "all":
            print(show_all(book))

        elif command == "add-birthday":
            print(add_birthday(args, book))

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        else:
            print("Invalid command. Type: add / change / phone / all / add-birthday / show-birthday / birthdays / exit")


if __name__ == "__main__":
    main()
