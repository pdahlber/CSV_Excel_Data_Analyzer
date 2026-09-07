import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

@st.cache_data(show_spinner=False)
def load_and_clean_data(file):
    #Determine the Type of the Uploaded file and Convert it into a Pandas DataFrame
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    #Check if the uploaded dataframe is empty with no rows. Display an error and Stop the app if it is.
    if df.empty:
        st.error(
            "The uploaded file is empty. "
            "Please upload a file containing data."
        )
        st.stop()
    #Remove rows with missing data & Duplicate Rows
    df_clean = df.dropna()
    df_clean = df_clean.drop_duplicates()

    return df, df_clean

@st.cache_data(show_spinner=False)
def detect_columns(df):
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
    # NUMERICAL COLUMNS
    # --------------------------------
    numerical_columns = df.select_dtypes(include="number").columns.tolist()

    return categorical_columns, date_columns, numerical_columns

# 1. Page Configuration (Sets up a clean layout)
st.set_page_config(page_title="AI Data Analyzer", page_icon="📊", layout="wide")

st.title("CSV & Excel Data Analyzer")
st.markdown("**Upload a CSV or Excel file to explore, filter, and analyze your data.**")

uploaded_file = st.file_uploader("Upload a file: ", type=["csv", "xlsx"])

if uploaded_file:
    try:
       #Call the Function to read-in and clean the dataset
        with st.spinner("Loading and cleaning your file..."):
            df, df_clean = load_and_clean_data(uploaded_file)

        #Display the Dataframe with an Expander
        st.header("Data Preview")
        st.markdown("**Preview the uploaded dataset before analyzing the data.**")
        with st.expander("View Dataset"):
            st.dataframe(df.head(100))
            st.caption("Showing the first 100 rows.")

        st.divider()

        #Display the Dataframe's Number of Rows and Columns side-by-side
        st.header("Dataset Overview")
        st.markdown("**View the size and basic structure of your dataset.**")
        col1, col2 = st.columns(2)
        col1.metric("Rows:", df.shape[0])
        col2.metric("Columns:", df.shape[1])

        st.divider()

        #Display Missing values and Duplicate Rows side by side
        st.header("Data Quality")
        st.markdown("**View the number of missing values and duplicate rows in your dataset.**")
        col1, col2 = st.columns(2)
        col1.metric("Missing Values:", df.isnull().sum().sum())
        col2.metric("Duplicate Rows:", df.duplicated().sum())
        
        # --------------------------------
        # Dataset Cleaning
        # --------------------------------

        #Original Row Count
        rows_before = len(df)

        #Cleaned Row Count & No. of Rows Removed
        rows_after = len(df_clean)
        rows_removed = rows_before - rows_after

        st.header("Cleaning Results")
        st.markdown("**See how the dataset changed after removing missing and duplicate records.**")

        col1, col2, col3 = st.columns(3)

        col1.metric("Rows Before Cleaning:", rows_before)
        col2.metric("Rows After Cleaning:", rows_after)
        col3.metric("Rows Removed:", rows_removed)

        with st.expander("View Cleaned Data"):
            st.dataframe(df_clean.head(100))
            st.caption("Showing the first 100 rows.")

        #Converts your cleaned DataFrame into CSV-formatted data. index=False prevents the Dataframe's index from becoming an extra column

        csv_data = df_clean.to_csv(index=False)
        #Give the user the option to Download the Cleaned Data.
        st.download_button(
            label="Download Cleaned Data",
            data=csv_data,
            file_name="cleaned_data.csv",
            mime="text/csv"
        )

        df = df_clean

        st.divider()

        st.header("Filters")
        st.markdown("**Filter the dataset by a particular category and date-range before performing your analysis.**")

        #Get the lists of available columns
        with st.spinner("Analyzing your columns..."):
            categorical_columns, date_columns, numerical_columns = detect_columns(df)

        # --------------------------------
        # FILTER CONTROLS
        # --------------------------------

        # Now we know what columns are available.

        #Start a Filter Mask with all True values
        filter_mask = pd.Series(True, index=df.index)

        col1, col2 = st.columns(2)

        # Category filter: Start filtering if the list of possible categorical columns is not empty.
        if categorical_columns:
            with col1:
                #Allow the user to specify their official "Category" column.
                st.caption("Choose a Categorical column if you would like to filter by Category.")
                category_column = st.selectbox(
                    "Category column:",
                    categorical_columns
                )

                #Extract all the unique values in the selected column, and give the option to use "All".
                categories = ["All"] + df[category_column].unique().tolist()

                #Allow the user to select a particular category, or just leave as "All".
                st.caption("Select a particular Category from that column, or leave as 'All' if you wish not to filter.")
                selected_category = st.selectbox(
                    "Selected category:",
                    categories
                )
            #If the user selects a category instead of leaving "All", update the filter mask.
            if selected_category != "All":
                filter_mask &= df[category_column] == selected_category

        #Display a warning if nothing is in the categorical columns list.
        else:
            with col1:
                st.warning(
                    "No suitable categorical columns were detected. "
                    "Category filtering is unavailable."
                )
     
        # Date filter: If the list of possible date columns is not empty, start filtering
        if date_columns:
            with col2:
                #Allow the user to choose their desired Date Column from the list
                st.caption("Choose your desired Date column if you would like to filter by date. Then specify your date-range.")
                date_column = st.selectbox(
                    "Date column:",
                    date_columns
                )

            #Convert the column into a datetime object
            converted_date = pd.to_datetime(
                df[date_column],
                errors="coerce",
                format="mixed"
            )
            with col2:
                #Allow the user to select a start date, setting its default as the minimum (earliest) and restrict its range.
                start_date = st.date_input(
                    "Start date:",
                    converted_date.min().date(),
                    min_value=converted_date.min().date(),
                    max_value=converted_date.max().date()
                )
                #Allow the user to select an end date, setting its default as the maximum (latest) and restrict its range.
                end_date = st.date_input(
                    "End date:",
                    converted_date.max().date(),
                    min_value=converted_date.min().date(),
                    max_value=converted_date.max().date()
                )

            #Update the filter mask by filtering between those 2 dates.
            filter_mask &= (
                (converted_date.dt.date >= start_date) &
                (converted_date.dt.date <= end_date)
            )
        #Display a warning if nothing is in the date columns list
        else:
            with col2:
                st.warning(
                    "No date column could be detected. "
                    "Date filtering is unavailable."
                )
           
        # --------------------------------
        # APPLY THE FILTERS
        # --------------------------------

        filtered_df = df[filter_mask]

        st.divider()

        #Display Summary Metrics
        st.header("Summary Metrics")
        st.markdown("**View basic statistics for a numerical column in your dataset.**")

        #Display a warning msg if no numerical columns were detected.
        if not numerical_columns:
            st.warning(
                "No numerical columns were detected. "
                "Summary metrics and numerical analysis are unavailable."
            )
        #Allow the user to select a numerical column for a quick Summary if any exist in the Dataframe
        else:
            st.caption("Choose a Numerical column in order to view some basic statistics on it.")
            metric_column = st.selectbox("Numerical column:", numerical_columns)

            #Calculate your Total, Average, and Number of Records
            total = filtered_df[metric_column].sum()
            average = filtered_df[metric_column].mean()
            number_of_records = len(filtered_df)
        
            #Display them side-by-side
            col1, col2, col3 = st.columns(3)

            col1.metric(f"Total: {metric_column}", f"{total:,.2f}")
            col2.metric(f"Average: {metric_column}", f"{average:,.2f}")
            col3.metric("Number of Records", number_of_records)

        st.divider()

        st.header("Data Analysis")
        st.markdown("""**Group and analyze your data using different columns and aggregation methods.** 
- Example: Total Revenue per Product Category.""")
        #Allow the user to select which columns they want to group and aggregate.

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
            col1, col2, col3 = st.columns(3)

            with col1:
                #Allow the user to choose a Categorical Column to Analyze.
                st.caption("Choose the Categorical column you want to group your data by.")
                group_column = st.selectbox("Group data by:", categorical_columns)

            with col2:
                #Allow the user to choose a Numerical Column to Analyze.
                st.caption("Choose the Numerical column you want to analyze.")
                value_column = st.selectbox("Analyze:", numerical_columns)

            with col3:
                #Allow the user to choose a type of aggregation.
                st.caption("Choose how you want to summarize the data.")
                aggregation = st.selectbox(
                    "Aggregation:",
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

            #Resetting the Dataframe index from the Category to the regular Numbered Dataframe Column
            results_df = grouped_data.reset_index()

            #Renaming the Columns as the Categorical Group Column and the Aggregated Value Column
            results_df.columns = [
                group_column,
                f"{aggregation} {value_column}"
            ]

            #Display the Grouped Analysis as a Dataframe
            st.dataframe(results_df, use_container_width=True)

            fig = px.bar(
                grouped_data,
                x=grouped_data.index,
                y=grouped_data.values,
                title=f"{aggregation}  {value_column}  per  {group_column}",
                labels={"x": group_column, "y": aggregation + " " + value_column}
            )

            st.plotly_chart(fig, use_container_width=True)   

            #Start a list of applied filters to add to the prompt
            filters_applied = []
            #If the user did not leave the category filter as "All", add it to the list.
            if selected_category != "All":
                filters_applied.append(
                    f"- {category_column}: {selected_category}"
                )
            #Check if date columns are detected. Then if a date filter is applied, add it to the list.
            if date_columns:
                #Date filter is applied if either the start or end dates are not equal to their default values.
                date_filter_applied = (
                    start_date != converted_date.min().date()
                    or
                    end_date != converted_date.max().date()
                )
                #Add the date filter to the list if the date filter is applied
                if date_filter_applied:
                    filters_applied.append(
                        f"- Date range: {start_date} to {end_date}"
                    )
            
            if filters_applied:
                #If the list is not empty, join the strings together with line separators.
                filters_applied = "\n".join(filters_applied)
            else:
                #Otherwise replace it with the word "None"
                filters_applied = "None"

            if st.button("Generate AI Insights"):
                #Take your grouped data and format it into a multi-line string.
                analysis_results = "\n".join(
                f"- {category}: {value:,.2f}  "
                for category, value in grouped_data.items()
            )

                prompt = f"""
You are a data analysis assistant. Analyze the following results from a
dataset and provide useful, concise insights.

SUMMARY METRICS
- Numerical column: {metric_column}
- Total: {total}
- Average: {average}
- Records Analyzed: {number_of_records}

GROUPED DATA ANALYSIS
Grouped by: {group_column}
Numerical column: {value_column}
Aggregation: {aggregation}

Filters applied:
{filters_applied}

Results:
{analysis_results}

Provide 3 concise bullet points describing the most important insights.
Focus on meaningful comparisons, differences, and patterns.
Do not simply repeat the values.
When relevant, incorporate the active filters into your insights.
"""
                try:
                    with st.spinner("Generating AI Insights..."):
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": prompt}]
                        )
                    st.write(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"Unable to generate AI insights. Error: {e}")

    except Exception as e:
        st.error(f"Unable to read the uploaded file. "
        f"Please make sure it is a valid CSV or Excel file. Error: {e}")
