import os
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()

token = os.getenv("TELEGRAM_TOKEN")
csv_file = "finance_data.csv"

if os.path.exists(csv_file):
    data = pd.read_csv(csv_file, parse_dates=["Date"])
else:
    data = pd.DataFrame(columns=["Date", "Category", "Amount", "Description", "Type"])


def save_data():
    data.to_csv(csv_file, index=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Добавить данные", callback_data="add_data")],
        [InlineKeyboardButton("Отчет за день", callback_data="daily_report")],
        [InlineKeyboardButton("Отчет за неделю", callback_data="weekly_report")],
        [InlineKeyboardButton("Отчет за месяц", callback_data="monthly_report")],
        [InlineKeyboardButton("Визуализация данных", callback_data="visualize")],
        [InlineKeyboardButton("Сбросить данные", callback_data="reset_data")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_data":
        await query.edit_message_text(
            text="Пожалуйста, отправьте данные в формате:\nДата, Категория, Сумма, Описание, Тип (например: 2024-11-01, Еда, 500, Ужин, Расход)"
        )
    elif query.data in ["daily_report", "weekly_report", "monthly_report"]:
        await generate_report(query, query.data)
    elif query.data == "visualize":
        await visualize_data(query)
    elif query.data == "reset_data":
        await reset_data(query)


async def add_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global data
    user_data = update.message.text.split(", ")

    if len(user_data) == 5:
        try:
            new_entry = pd.DataFrame(
                [
                    [
                        pd.to_datetime(
                            user_data[0], format="%Y-%m-%d", errors="coerce"
                        ),
                        user_data[1],
                        float(user_data[2]),
                        user_data[3],
                        user_data[4],
                    ]
                ],
                columns=data.columns,
            )
            if new_entry["Date"].isna().any():
                raise ValueError("Неверный формат даты.")

            data = pd.concat([data, new_entry], ignore_index=True)
            save_data()
            await update.message.reply_text("Данные успешно добавлены!")
        except ValueError as e:
            await update.message.reply_text(f"Ошибка: {e}")
    else:
        await update.message.reply_text("Неверный формат. Пожалуйста, повторите ввод.")


async def generate_report(query, period):
    global data
    today = pd.to_datetime("today").normalize()

    if period == "daily_report":
        report = data[data["Date"] == today]
    elif period == "weekly_report":
        report = data[data["Date"] >= today - pd.DateOffset(weeks=1)]
    elif period == "monthly_report":
        report = data[data["Date"] >= today - pd.DateOffset(months=1)]

    if report.empty:
        await query.edit_message_text(text="Нет данных за выбранный период.")
        return

    report_summary = report.groupby("Category")["Amount"].sum().reset_index()
    report_text = f"Отчет за {period.replace('_', ' ')}:\n"
    for index, row in report_summary.iterrows():
        report_text += f"{row['Category']}: {row['Amount']}\n"

    await query.edit_message_text(text=report_text)


async def visualize_data(query):
    global data
    if data.empty or data["Amount"].isna().all():
        await query.edit_message_text(text="Нет данных для визуализации.")
        return

    category_sums = data.groupby("Category")["Amount"].sum()
    if not category_sums.empty:
        plt.figure(figsize=(10, 6))
        plt.pie(
            category_sums, labels=category_sums.index, autopct="%1.1f%%", startangle=90
        )
        plt.title("Расходы по категориям")
        plt.axis("equal")

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()
        await query.message.reply_photo(photo=buf)
    else:
        await query.edit_message_text(text="Нет данных для визуализации.")


async def reset_data(query):
    global data
    data = pd.DataFrame(columns=["Date", "Category", "Amount", "Description", "Type"])
    save_data()
    await query.edit_message_text(text="Все данные сброшены!")


def main():
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_data))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()


if __name__ == "__main__":
    main()
