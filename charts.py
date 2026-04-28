import io
import pandas as pd
import matplotlib
import string
from datetime import datetime


matplotlib.use('Agg')
import matplotlib.pyplot as plt


def build_contacts_dataframe(contacts): #Converts a list of contact objects into a pandas DataFrame
    data = []

    for c in contacts:
        data.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'email': c.email,
            'birthday': c.birthday.isoformat() if c.birthday else None
        })

    df = pd.DataFrame(data)

    if df.empty:
        df = pd.DataFrame(columns=['id', 'name', 'phone', 'email', 'birthday'])

    return df


def generate_overview_chart(contacts):
    df = build_contacts_dataframe(contacts)

    # Предполагаем, что есть колонка с именем (например 'name')
    if 'name' not in df.columns:
        raise ValueError("Column 'name' not found in contacts data")

    # Берём первую букву имени
    first_letters = (
        df['name']
        .fillna('')
        .astype(str)
        .str.strip()
        .str[0]
        .str.upper()
    )

    # Оставляем только английские буквы
    letters = list(string.ascii_uppercase)
    counts = {letter: 0 for letter in letters}

    for letter in first_letters:
        if letter in counts:
            counts[letter] += 1

    labels = list(counts.keys())
    values = list(counts.values())

    # Строим график
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, values)

    ax.set_title('Contacts by First Letter')
    ax.set_xlabel('Alphabet (A-Z)')
    ax.set_ylabel('Number of Contacts')

    # Подписи значений
    for bar, value in zip(bars, values):
        if value > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                str(value),
                ha='center',
                va='bottom'
            )

    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close(fig)
    img.seek(0)

    return img


def generate_birthdays_chart(contacts):   #Generates a chart showing birthday distribution by month
    df = build_contacts_dataframe(contacts)

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_counts = [0] * 12

    if not df.empty and 'birthday' in df.columns:
        birthday_df = df[df['birthday'].notna()].copy()

        if not birthday_df.empty:
            birthday_df['birthday'] = pd.to_datetime(birthday_df['birthday'], errors='coerce')
            birthday_df = birthday_df.dropna(subset=['birthday'])

            counts = birthday_df['birthday'].dt.month.value_counts().sort_index()

            for month, count in counts.items():
                month_counts[int(month) - 1] = int(count)

    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.bar(month_names, month_counts)

    ax.set_title('Birthdays by Month')
    ax.set_ylabel('Count')
    ax.set_ylim(0, max(month_counts + [1]) + 1)

    for bar, value in zip(bars, month_counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            str(value),
            ha='center',
            va='bottom'
        )

    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close(fig)
    img.seek(0)

    return img


def generate_age_histogram(contacts):
    df = build_contacts_dataframe(contacts)

    if df.empty or 'birthday' not in df.columns:
        raise ValueError("No birthday data available")

    # Убираем пустые значения
    df = df[df['birthday'].notna()].copy()

    if df.empty:
        raise ValueError("No valid birthdays found")

    # Преобразуем в datetime
    df['birthday'] = pd.to_datetime(df['birthday'], errors='coerce')
    df = df.dropna(subset=['birthday'])

    # Текущая дата
    today = datetime.today()

    # Считаем возраст
    df['age'] = df['birthday'].apply(
        lambda b: today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    )

    # Строим гистограмму
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(df['age'], bins=10)

    ax.set_title('Age Distribution')
    ax.set_xlabel('Age')
    ax.set_ylabel('Number of Contacts')

    plt.tight_layout()

    # Сохраняем в память
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close(fig)
    img.seek(0)

    return img