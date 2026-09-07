import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration (Sets up a clean layout)
st.set_page_config(page_title="AI Data Analyzer", page_icon="📊", layout="wide")

st.title("CSV & Excel Data Analyzer")
st.write("Upload a CSV or Excel file to explore, filter, and analyze your data.")

uploaded_file = st.file_uploader("Upload a file: ", type=["csv", "xlsx"])

if uploaded_file:
    try:
        #Determine the Type of the Uploaded file and Convert it into a Pandas DataFrame
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
       
        #Display the Dataframe
        st.header("Data Preview")
        st.dataframe(df)

        #Display the Dataframe's Number of Rows and Columns side-by-side
        st.header("Dataset Overview")
        col1, col2 = st.columns(2)
        col1.metric("Rows:", df.shape[0])
        col2.metric("Columns:", df.shape[1])

        #Display Missing values and Duplicate Rows side by side
        st.header("Data Quality")
        col1, col2 = st.columns(2)
        col1.metric("Missing Values:", df.isnull().sum().sum())
        col2.metric("Duplicate Rows:", df.duplicated().sum())
        
        # --------------------------------
        # Dataset Cleaning
        # --------------------------------

        #Original Row Count
        rows_before = len(df)

        #Remove rows with missing data & Duplicate Rows
        df_clean = df.dropna()
        df_clean = df_clean.drop_duplicates()

        #Cleaned Row Count & No. of Rows Removed
        rows_after = len(df_clean)
        rows_removed = rows_before - rows_after

        st.header("Cleaning Results")

        col1, col2, col3 = st.columns(3)

        col1.metric("Rows Before Cleaning", rows_before)
        col2.metric("Rows After Cleaning", rows_after)
        col3.metric("Rows Removed", rows_removed)

        st.write("Cleaned Data:")
        st.dataframe(df_clean)

        df = df_clean

        st.header("Filters")

        # --------------------------------
        # CATEGORY DETECTION
        # --------------------------------

        categorical_columns = []
        row_count = len(df)
        for column in df.columns:

            #Skip any column that is not a string type.
            if not pd.api.types.is_string_dtype(df[column]):
                continue

            #Get the number of unique values in the column
            unique_count = df[column].nunique()

            #Keep any column with no more than 20 unique values, which are within 50% of the total rows
            if unique_count <= 20 and unique_count / row_count <= 0.5:
                categorical_columns.append(column)

        # --------------------------------
        # DATE DETECTION
        # --------------------------------

        date_columns = []

        for column in df.columns:

            #Skip any purely numeric columns.
            if pd.api.types.is_numeric_dtype(df[column]):
                continue

            #Convert the column into a datetime object
            converted = pd.to_datetime(
                df[column],
                errors="coerce",
                format="mixed"
            )
            #Calcuate the percentage of successfully converted rows in the column
            success_rate = converted.notna().mean()

            #Keep any column with a success rate of at east 80%
            if success_rate >= 0.8:
                date_columns.append(column)
         
        # --------------------------------
        # FILTER CONTROLS
        # --------------------------------

        # Now we know what columns are available.

        #Start a Filter Mask with a True values
        filter_mask = pd.Series(True, index=df.index)

        # Category filter: Start filtering if the list of possible categorical columns is not empty.
        if categorical_columns:

            #Allow the user to specify their official "Category" column.
            category_column = st.selectbox(
                "Category column:",
                categorical_columns
            )

            #Extract all the unique values in the selected column, and give the option to use "All".
            categories = ["All"] + df[category_column].unique().tolist()

            #Allow the user to select a particular category, or just leave as "All".
            selected_category = st.selectbox(
                "Select a category:",
                categories
            )
            #If the user selects a category instead of leaving "All", update the filter mask.
            if selected_category != "All":
                filter_mask &= df[category_column] == selected_category

        #Display a warning if nothing is in the categorical columns list.
        else:
            st.warning(
                "No suitable categorical columns were detected. "
                "Category filtering is unavailable."
            )
     
        # Date filter: If the list of possible date columns is not empty, start filtering
        if date_columns:

            #Extract the first column from the list.
            #Note:Consider adding a drop-down to display the detected date columns in case the
            # dateset has more than one.
            date_column = date_columns[0]

            #Convert the column into a datetime object
            df[date_column] = pd.to_datetime(
                df[date_column],
                errors="coerce",
                format="mixed"
            )
            #Allow the user to select a start date, setting its default as the minimum (earliest)
            start_date = st.date_input(
                "Start date:",
                df[date_column].min().date()
            )
            #Allow the user to select an end date, setting its default as the maximum (latest)
            end_date = st.date_input(
                "End date:",
                df[date_column].max().date()
            )
            #Update the filter mask by filtering between those 2 dates.
            filter_mask &= (
                (df[date_column].dt.date >= start_date) &
                (df[date_column].dt.date <= end_date)
            )
        #Display a warning if nothing is in the date columns list
        else:
            st.warning(
                "No date column could be detected. "
                "Date filtering is unavailable."
            )
           
        # --------------------------------
        # APPLY THE FILTERS
        # --------------------------------

        filtered_df = df[filter_mask]

        #Display Summary Metrics
        st.header("Summary Metrics")

        # Numerical column
        numerical_columns = df.select_dtypes(include="number").columns.tolist()

        #Display a warning msg if no numerical columns were detected.
        if not numerical_columns:
            st.warning(
                "No numerical columns were detected. "
                "Summary metrics and numerical analysis are unavailable."
            )
        #Allow the user to select a numerical column for a quick Summary if any exist in the Dataframe
        else:
            metric_column = st.selectbox("Numerical column:", numerical_columns)

            #Calculate your Total, Average, and Number of Records
            total_sales = filtered_df[metric_column].sum()
            average_sale = filtered_df[metric_column].mean()
            number_of_records = len(filtered_df)
        
        #Display them side-by-side
        col1, col2, col3 = st.columns(3)

        col1.metric(f"Total: {metric_column}", f"${total_sales:,.2f}")
        col2.metric(f"Average: {metric_column}", f"${average_sale:,.2f}")
        col3.metric("Number of Records", number_of_records)

        st.header("Data Analysis")
        #Allow the user to select which columns they want to group and aggregate.

        #Start by extracting the Categorical columns. Then allow the user to choose one.
        categorical_columns = df.select_dtypes(include="object").columns.tolist()

        #Display a warning if no Categorical Column is Detected
        if not categorical_columns:
            st.warning(
                "Data Analysis is unavailable because no suitable "
                "categorical columns were detected."
            )
        #Display a warning if no Numerical Column is Detected
        elif not numerical_columns:
            st.warning(
                "Data Analysis is unavailable because no numerical "
                "columns were detected."
            )
        #Run through the Analysis if both Column types are present in the Dataframe.
        else:
            #Allow the user to choose a Categorical Column to Analyze.
            group_column = st.selectbox("Group data by:", categorical_columns)

            #Allow the user to choose a Numerical Column to Analyze.
            value_column = st.selectbox("Analyze:", numerical_columns)

            #Allow the user to choose a type of aggregation.
            aggregation = st.selectbox(
                "Choose an aggregation:",
                ["Total", "Average", "Count", "Minimum", "Maximum"]
            )
            #Use conditionals to perform the desired aggregation based on the user's selection.
            if aggregation == "Total":
                grouped_data = filtered_df.groupby(group_column)[value_column].sum()
       
            elif aggregation == "Average":
                grouped_data = filtered_df.groupby(group_column)[value_column].mean()

            elif aggregation == "Count":
                grouped_data = filtered_df.groupby(group_column)[value_column].count()

            elif aggregation == "Minimum":
                grouped_data = filtered_df.groupby(group_column)[value_column].min()

            elif aggregation == "Maximum":
                grouped_data = filtered_df.groupby(group_column)[value_column].max()

            st.write(grouped_data)
            fig = px.bar(
                grouped_data,
                x=grouped_data.index,
                y=grouped_data.values,
                title=f"{aggregation}  {value_column}  per  {group_column}",
                labels={"x": group_column, "y": aggregation + " " + value_column}
            )

            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error parsing file: {e}")
