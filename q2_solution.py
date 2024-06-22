import pandas as pd


def print_analytics(df_with_bookings, df_without_bookings):
    print("------------- Analytics ----------------")
    print(f"Persons with bookings: {len(df_with_bookings)}")
    print(f"Persons without bookings: {len(df_without_bookings)}")

    # Additional analytics
    print("\n-- Additional Analytics --")
    print(f"Unique Majors: {df_with_bookings['majorIds'].nunique()}")
    print(f"Unique States: {df_with_bookings['state'].nunique()}")
    print(
        f"Average Age of Persons: {df_with_bookings['dob'].apply(lambda x: pd.to_datetime('today').year - pd.to_datetime(x).year).mean():.2f}"
    )


def print_assumptions():
    print("------------- Assumptions ----------------")
    print(
        "No zip code is provided in address of person so extracting that column isn't possible."
    )
    print("We are extracting city and state from person address.")
    print("Successful record will have at least one booking.")
    print(
        "Email column can't be unique as multiple records with same email are present."
    )
    print(
        "Address1 definition is ambiguous, So i am checking it based on street, state and city values. To make address1 all values should present"
    )
    print(
        "Address1 will include street name and address2 will include city and state combination."
    )


def print_data_cleaning_strategy():
    print("------------- Data Cleaning Strategy ----------------")
    print(
        "Drop duplicate combination of personId and email just to make sure data is unique."
    )
    print("Verify all emails are valid.")
    print(
        "Replacing null data with empty string in case of dob, city, state, majorIds, address1 and address2"
    )
    print("Drop columns firstName and lastName and merge it as new name column.")
    print("Only keep addresses that have both city and state components.")


def load_data(inventory_path, majors_path, occupancy_path, persons_path):
    try:
        df_inventory = pd.read_csv(inventory_path)
        df_majors = pd.read_csv(majors_path)
        df_occupancy = pd.read_csv(occupancy_path)
        df_persons = pd.read_csv(persons_path)
    except FileNotFoundError as e:
        print(f"Error: {e.filename} not found.")
        return None, None, None, None
    except pd.errors.EmptyDataError as e:
        print(f"Error: {e.args[0]}")
        return None, None, None, None
    except pd.errors.ParserError as e:
        print(f"Error parsing CSV: {e.args[0]}")
        return None, None, None, None

    return df_inventory, df_majors, df_occupancy, df_persons


def validate_email(email):
    return isinstance(email, str) and "@" in email and "." in email


def parse_date(date_str):
    try:
        return pd.to_datetime(date_str).date()
    except:
        return None


def extract_city_state(address):
    parts = address.split(", ")
    address1 = parts[0] if len(parts) > 0 else None
    city = parts[1] if len(parts) > 1 else None
    state = parts[2] if len(parts) > 2 else None
    address2 = f"{city}, {state}"
    return address1, city, state, address2


def map_major_ids(major_names, major_dict):
    if pd.isna(major_names):
        return ""  # Return empty string if major_names is NaN
    ids = [
        major_dict.get(m.strip(), "")
        for m in major_names.split(",")  # Split only if not NaN
        if m.strip() != ""
    ]
    return ",".join(ids)


def merge_data(df_inventory, df_majors, df_occupancy, df_persons):
    try:
        df_occupancy_merged = pd.merge(
            df_occupancy,
            df_inventory[["buildingName", "roomName", "bedName", "bedId"]],
            on=["buildingName", "roomName", "bedName"],
            how="left",
        )

        df_persons_merged = pd.merge(
            df_occupancy_merged,
            df_persons,
            on=["personId"],
            how="left",
        )

        major_dict = dict(zip(df_majors["name"], df_majors["id"]))

        df_persons_merged["majorIds"] = df_persons_merged["majors"].apply(
            lambda x: map_major_ids(x, major_dict)
        )

    except KeyError as e:
        print(f"Error: {e}. Column not found in one of the DataFrames.")
        return None

    return df_persons_merged


def clean_data(df):
    duplicates_to_drop = df[df.duplicated(subset=["personId", "email"], keep=False)]
    if not duplicates_to_drop.empty:
        print("Duplicate Rows to be Dropped:")
        print(duplicates_to_drop)

    # Drop duplicates based on personId and email
    df.drop_duplicates(subset=["personId", "email"], inplace=True)

    # Validate and parse dates
    df["dob"] = df["dob"].apply(parse_date)

    # Validate email addresses
    df = df[df["email"].apply(validate_email)]

    # Combine firstName and lastName into name
    df["name"] = df["firstName"] + " " + df["lastName"]

    df.drop(columns=["firstName", "lastName"], inplace=True)

    df[["address1", "address2", "city", "state"]] = df["address"].apply(
        lambda x: pd.Series(extract_city_state(x))
    )

    invalid_data = df[
        df["dob"].isnull()
        | df["email"].apply(lambda x: not validate_email(x))
        | df["city"].isnull()
        | df["state"].isnull()
    ]
    if not invalid_data.empty:
        print("Rows with Invalid or Missing Data to be Excluded:")
        print(invalid_data)

    # Keep addresses only if they form a full address
    df = df[(df["address1"].notna()) & (df["city"].notna()) & (df["state"].notna())]

    # Fill missing values with empty strings
    df["majorIds"].fillna("", inplace=True)
    df["address1"].fillna("", inplace=True)
    df["address2"].fillna("", inplace=True)
    df["city"].fillna("", inplace=True)
    df["state"].fillna("", inplace=True)
    df["dob"].fillna("", inplace=True)

    return df


def save_data(df, filename):
    df.to_csv(filename, index=False)


def main():
    # Load data from CSV files
    df_inventory, df_majors, df_occupancy, df_persons = load_data(
        "inventory_data.csv",
        "majors_data.csv",
        "occupancy_data.csv",
        "persons_data.csv",
    )

    if any(df is None for df in [df_inventory, df_majors, df_occupancy, df_persons]):
        print("Error: Failed to load data. Check input files.")
        return

    # Merge the data
    df_final = merge_data(df_inventory, df_majors, df_occupancy, df_persons)

    if df_final is None:
        print("Error: Failed to merge data.")
        return

    # Clean the merged data
    df_final = clean_data(df_final)

    if df_final.empty:
        print("Error: No valid data after cleaning.")
        return

    # Select and reorder final columns
    columns_final = [
        "personId",
        "name",
        "email",
        "dob",
        "address1",
        "address2",
        "city",
        "state",
        "majorIds",
        "bedId",
    ]
    df_with_bookings = df_final[columns_final]

    # Save the cleaned and merged data to a CSV file
    save_data(df_with_bookings, "person_with_bookings.csv")

    # Identify and print excluded rows due to incomplete or invalid data
    major_dict = dict(zip(df_majors["name"], df_majors["id"]))
    df_without_bookings = df_persons[
        ~df_persons["personId"].isin(df_with_bookings["personId"])
    ].copy()
    df_without_bookings.loc[:, "majorIds"] = df_without_bookings["majors"].apply(
        lambda x: map_major_ids(x, major_dict)
    )
    df_without_bookings.loc[:, "bedId"] = ""
    df_without_bookings.drop(columns=["majors"], inplace=True)
    df_without_bookings = clean_data(df_without_bookings)
    df_without_bookings = df_without_bookings[columns_final]

    if not df_without_bookings.empty:
        print("Excluded Rows due to incomplete or invalid data:")
        print(df_without_bookings.head())
        save_data(df_without_bookings, "person_without_bookings.csv")
    else:
        print("No rows were excluded.")

    return df_with_bookings, df_without_bookings


if __name__ == "__main__":
    print_assumptions()
    print_data_cleaning_strategy()
    df_with_bookings, df_without_bookings = main()
    print_analytics(df_with_bookings, df_without_bookings)
