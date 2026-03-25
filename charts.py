import io
import pandas as pd
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


def build_contacts_dataframe(contacts):
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

    total_contacts = len(df)
    with_email = 0
    with_birthday = 0

    if 'email' in df.columns:
        with_email = df['email'].fillna('').astype(str).str.strip().ne('').sum()

    if 'birthday' in df.columns:
        with_birthday = df['birthday'].notna().sum()

    labels = ['Contacts', 'With Email', 'With Birthday']
    values = [int(total_contacts), int(with_email), int(with_birthday)]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(labels, values)

    ax.set_title('Contacts Overview')
    ax.set_ylabel('Count')
    ax.set_ylim(0, max(values + [1]) + 2)

    for bar, value in zip(bars, values):
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


def generate_birthdays_chart(contacts):
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