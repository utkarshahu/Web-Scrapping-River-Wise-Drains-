from scrap import (
    generate_csv_from_html,
    clear_current,
    load_csv
)

def manual_refresh():

    print("\n===== MANUAL REFRESH =====")

    generate_csv_from_html()

    clear_current()

    load_csv()

    print("Manual Refresh Completed")


if __name__ == "__main__":

    manual_refresh()