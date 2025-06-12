import pandas as pd


def load_data(file_path):
    df = pd.read_json(file_path)
    return df


if __name__ == "__main__":
    df = load_data("data/instance1.json")
    print(df)
