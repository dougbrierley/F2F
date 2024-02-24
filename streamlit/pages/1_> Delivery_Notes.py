import streamlit as st
import pandas as pd
import io
import base64

st.set_page_config(page_title="Delivery Notes Generator")


hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("Delivery Notes Generator")

st.markdown("Upload weekly order excel and contacts CSV to generate delivery notes.")

order_sheet = st.file_uploader("Choose Weekly Order Excel", type="xlsx", accept_multiple_files=False)
contacts = st.file_uploader("Choose Contacts CSV", type="xlsx", accept_multiple_files=False)
dataframes = []

if order_sheet and contacts:
    orders = pd.read_excel(order_sheet)
    

    # if len(dataframes) > 1:
    #     merge = st.checkbox("Merge uploaded CSV files")

    #     if merge:
    #         # Merge options
    #         keep_first_header_only = st.selectbox("Keep only the header (first row) of the first file", ["Yes", "No"])
    #         remove_duplicate_rows = st.selectbox("Remove duplicate rows", ["No", "Yes"])
    #         remove_empty_rows = st.selectbox("Remove empty rows", ["Yes", "No"])
    #         end_line = st.selectbox("End line", ["\\n", "\\r\\n"])

    #         try:
    #             if keep_first_header_only == "Yes":
    #                 for i, df in enumerate(dataframes[1:]):
    #                     df.columns = dataframes[0].columns.intersection(df.columns)
    #                     dataframes[i+1] = df

    #             merged_df = pd.concat(dataframes, ignore_index=True, join='outer')

    #             if remove_duplicate_rows == "Yes":
    #                 merged_df.drop_duplicates(inplace=True)

    #             if remove_empty_rows == "Yes":
    #                 merged_df.dropna(how="all", inplace=True)

    #             dataframes = [merged_df]

    #         except ValueError as e:
    #             st.error("Please make sure columns match in all files. If you don't want them to match, select 'No' in the first option.")
    #             st.stop()

    # # Show or hide DataFrames
    # show_dataframes = st.checkbox("Show DataFrames", value=True)

    # if show_dataframes:
    #     for i, df in enumerate(dataframes):
    #         st.write(f"DataFrame {i + 1}")
    #         st.dataframe(df)

    # if st.button("Download cleaned data"):
    #     for i, df in enumerate(dataframes):
    #         csv = df.to_csv(index=False)
    #         b64 = base64.b64encode(csv.encode()).decode()
    #         href = f'<a href="data:file/csv;base64,{b64}" download="cleaned_data_{i + 1}.csv">Download cleaned_data_{i + 1}.csv</a>'
    #         st.markdown(href, unsafe_allow_html=True)
else:
    st.warning("Please upload CSV file(s).")
    st.stop()

st.markdown("")
st.markdown("---")
st.markdown("")
st.markdown("<p style='text-align: center'><a href='https://github.com/Kaludii'>Github</a> | <a href='https://huggingface.co/Kaludi'>HuggingFace</a></p>", unsafe_allow_html=True)