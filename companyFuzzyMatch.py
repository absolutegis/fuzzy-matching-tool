import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz, process

# Set Streamlit to wide mode for full-screen width
st.set_page_config(layout="wide")

# Function to highlight matching characters from left to right and count them
def highlight_and_count_matches(text1, text2):
    highlighted_text1, highlighted_text2 = "", ""
    i = 0
    match_count = 0

    # Convert both strings to lowercase for case-insensitive comparison
    text1_lower = text1.lower()
    text2_lower = text2.lower()

    # Compare characters from left to right
    while i < min(len(text1_lower), len(text2_lower)) and text1_lower[i] == text2_lower[i]:
        highlighted_text1 += f'<span style="background-color: #d4edda;">{text1[i]}</span>'
        highlighted_text2 += f'<span style="background-color: #d4edda;">{text2[i]}</span>'
        match_count += 1
        i += 1

    # Append the remaining non-matching parts
    highlighted_text1 += text1[i:]
    highlighted_text2 += text2[i:]

    return highlighted_text1, highlighted_text2, match_count

# Function to perform fuzzy matching and include additional columns
def perform_fuzzy_matching(df1, df2, col1, col2, threshold, additional_cols1, additional_cols2):
    good_matches, poor_matches = [], []
    for idx1, name1 in df1[col1].fillna('').astype(str).items():  # Handle NaN and convert to string
        match_tuple = process.extractOne(name1, df2[col2].fillna('').astype(str), scorer=fuzz.ratio)
        if match_tuple:
            match, score, idx2 = match_tuple
            row_data = [idx1, name1, match, score]
            
            # Add matching characters count before additional columns
            _, _, match_count = highlight_and_count_matches(name1, match)
            row_data.append(match_count)

            # Append additional column values from df1 and df2
            row_data += list(df1.loc[idx1, additional_cols1]) + list(df2.loc[idx2, additional_cols2])

            if score >= threshold:
                good_matches.append(row_data)
            else:
                poor_matches.append(row_data)
    return good_matches, poor_matches

# Pagination function to limit records displayed per page
def paginate_dataframe(df, page_size, page_number):
    return df.iloc[page_size * (page_number - 1):page_size * page_number]

# Add a logo and title at the top of the page
st.image("https://storage.googleapis.com/absolute_gis_public/Images/absolute%20gis%20logo.png", width=250)
st.title("Fuzzy Matching Tool")

# File upload
file1 = st.file_uploader("Upload the first CSV/XLS file", type=["csv", "xlsx"])
file2 = st.file_uploader("Upload the second CSV/XLS file", type=["csv", "xlsx"])

# Initialize session state for moving records
if 'selected_to_move' not in st.session_state:
    st.session_state['selected_to_move'] = []

if 'good_matches' not in st.session_state:
    st.session_state['good_matches'] = pd.DataFrame()

if 'poor_matches' not in st.session_state:
    st.session_state['poor_matches'] = pd.DataFrame()

# If both files are uploaded
if file1 and file2:
    # Read the files
    df1 = pd.read_csv(file1) if file1.name.endswith('csv') else pd.read_excel(file1, engine='openpyxl')
    df2 = pd.read_csv(file2) if file2.name.endswith('csv') else pd.read_excel(file2, engine='openpyxl')

    # Select the columns to match on
    col1 = st.selectbox("Select column from first file for matching", df1.columns)
    col2 = st.selectbox("Select column from second file for matching", df2.columns)

    # Allow selection of additional columns to include in the results
    additional_cols1 = st.multiselect("Select additional columns from the first file", df1.columns)
    additional_cols2 = st.multiselect("Select additional columns from the second file", df2.columns)

    if col1 and col2:
        threshold = st.slider("Set the similarity score threshold", 0, 100, 94)

        # Ensure we only run matching after columns have been selected
        if st.button("Run Fuzzy Matching"):
            # Perform the fuzzy matching and store results in session state
            good_matches, poor_matches = perform_fuzzy_matching(df1, df2, col1, col2, threshold, additional_cols1, additional_cols2)
            # Include additional columns and the new match count column in the result
            columns = ['Index', col1, col2, 'Score', 'Matching Characters'] + additional_cols1 + additional_cols2
            st.session_state['good_matches'] = pd.DataFrame(good_matches, columns=columns)
            st.session_state['poor_matches'] = pd.DataFrame(poor_matches, columns=columns)

        # Pagination and sorting for Good Matches
        st.write("### Good Matches")
        good_matches_df = st.session_state['good_matches']
        if not good_matches_df.empty:
            # Allow sorting by selecting a column
            sort_column = st.selectbox("Sort by column (Good Matches)", good_matches_df.columns)
            sort_order = st.radio("Sort order", ["Ascending", "Descending"])
            ascending = sort_order == "Ascending"
            good_matches_df = good_matches_df.sort_values(by=sort_column, ascending=ascending)

            # Set page size and calculate total pages
            page_size = 20
            total_good_pages = (len(good_matches_df) // page_size) + 1
            st.write(f"Total Good Matches pages: {total_good_pages}")
            good_page_number = st.number_input("Good Matches - Page Number", min_value=1, max_value=total_good_pages, value=1)

            # Paginate Good Matches
            paginated_good_matches = paginate_dataframe(good_matches_df, page_size, good_page_number)

            # Display Good Matches and selection dropdown side by side
            col1_good, col2_good = st.columns([6, 1])  # Adjust the ratio to make the dropdown narrower
            with col1_good:
                good_matches_html = paginated_good_matches.copy()
                for idx, row in good_matches_html.iterrows():
                    name1, name2 = row[col1], row[col2]
                    highlighted_name1, highlighted_name2, _ = highlight_and_count_matches(name1, name2)
                    good_matches_html.at[idx, col1] = highlighted_name1
                    good_matches_html.at[idx, col2] = highlighted_name2
                # Display table without the index column
                st.write(good_matches_html.to_html(index=False, escape=False), unsafe_allow_html=True)

            # Move "Select records to move to Poor Matches" dropdown next to Good Matches table
            with col2_good:
                st.write("")  # Add some space above the dropdown for alignment
                move_to_poor = st.multiselect("Select records to move to Poor Matches", st.session_state['good_matches']['Index'])

                if st.button("Move to Poor Matches"):
                    # Move selected rows from Good Matches to Poor Matches
                    selected_rows = st.session_state['good_matches'][st.session_state['good_matches']['Index'].isin(move_to_poor)]
                    st.session_state['poor_matches'] = pd.concat([st.session_state['poor_matches'], selected_rows]).drop_duplicates().reset_index(drop=True)
                    st.session_state['good_matches'] = st.session_state['good_matches'][~st.session_state['good_matches']['Index'].isin(move_to_poor)].reset_index(drop=True)
                    st.cache_data.clear()  # Clear the cached data to refresh the tables

        # Pagination and sorting for Poor Matches
        st.write("### Poor Matches")
        poor_matches_df = st.session_state['poor_matches']
        if not poor_matches_df.empty:
            # Allow sorting by selecting a column
            sort_column_poor = st.selectbox("Sort by column (Poor Matches)", poor_matches_df.columns)
            sort_order_poor = st.radio("Sort order (Poor Matches)", ["Ascending", "Descending"])
            ascending_poor = sort_order_poor == "Ascending"
            poor_matches_df = poor_matches_df.sort_values(by=sort_column_poor, ascending=ascending_poor)

            # Set page size and calculate total pages
            total_poor_pages = (len(poor_matches_df) // page_size) + 1
            st.write(f"Total Poor Matches pages: {total_poor_pages}")
            poor_page_number = st.number_input("Poor Matches - Page Number", min_value=1, max_value=total_poor_pages, value=1)

            # Paginate Poor Matches
            paginated_poor_matches = paginate_dataframe(poor_matches_df, page_size, poor_page_number)

            # Display Poor Matches and selection dropdown side by side
            col1_poor, col2_poor = st.columns([6, 1])  # Adjust the ratio to make the dropdown narrower
            with col1_poor:
                poor_matches_html = paginated_poor_matches.copy()
                for idx, row in poor_matches_html.iterrows():
                    name1, name2 = row[col1], row[col2]
                    highlighted_name1, highlighted_name2, _ = highlight_and_count_matches(name1, name2)
                    poor_matches_html.at[idx, col1] = highlighted_name1
                    poor_matches_html.at[idx, col2] = highlighted_name2
                # Display table without the index column
                st.write(poor_matches_html.to_html(index=False, escape=False), unsafe_allow_html=True)

            with col2_poor:
                st.write("")  # Add some space above the dropdown for alignment
                move_to_good = st.multiselect("Select records to move to Good Matches", st.session_state['poor_matches']['Index'])

                if st.button("Move to Good Matches"):
                    # Move selected rows from Poor Matches to Good Matches
                    selected_rows = st.session_state['poor_matches'][st.session_state['poor_matches']['Index'].isin(move_to_good)]
                    st.session_state['good_matches'] = pd.concat([st.session_state['good_matches'], selected_rows]).drop_duplicates().reset_index(drop=True)
                    st.session_state['poor_matches'] = st.session_state['poor_matches'][~st.session_state['poor_matches']['Index'].isin(move_to_good)].reset_index(drop=True)
                    st.cache_data.clear()  # Clear the cached data to refresh the tables

        # Summary Information
        st.write("### Summary Information")
        st.write(f"Total records processed: {len(df1)}")
        st.write(f"Number of matches above threshold: {len(st.session_state['good_matches'])}")
        st.write(f"Number of poor matches below threshold: {len(st.session_state['poor_matches'])}")

        # Download functionality for both tables
        st.write("### Download Results")

        # Convert DataFrames to CSV
        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')

        good_matches_csv = convert_df_to_csv(st.session_state['good_matches'])
        poor_matches_csv = convert_df_to_csv(st.session_state['poor_matches'])

        st.download_button("Download Good Matches as CSV", good_matches_csv, "good_matches.csv", "text/csv")
        st.download_button("Download Poor Matches as CSV", poor_matches_csv, "poor_matches.csv", "text/csv")
