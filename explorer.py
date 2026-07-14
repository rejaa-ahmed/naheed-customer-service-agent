import streamlit as st
import pandas as pd
import re
import sys
import os

# Ensure the project root is in the path to correctly import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import DatabaseManager
from utils.logger import get_logger

logger = get_logger("explorer")

st.set_page_config(page_title="Database Explorer", layout="wide")

def fetch_data(query, params=None):
    try:
        with DatabaseManager() as conn:
            logger.info("Executing query...")
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
    except Exception as e:
        logger.error(f"Query Error: {e} | Query: {query}")
        st.error(f"Query Execution Error: {e}")
        return None

st.title("Database Explorer")

# Sidebar Navigation
mode = st.sidebar.radio("Navigation", ["Table Explorer", "Column Search", "Read-Only SQL Console"])

if mode == "Table Explorer":
    st.header("Table Explorer")
    st.write("Browse and inspect table schema, keys, and preview data.")
    
    search_kw = st.text_input("Search Tables by Keyword (leave empty for all)", "")
    
    # Query to fetch tables quickly from INFORMATION_SCHEMA
    query = "SELECT TABLE_NAME, TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()"
    params = []
    
    if search_kw.strip():
        query += " AND TABLE_NAME LIKE %s"
        params.append(f"%{search_kw}%")
        
    tables = fetch_data(query, tuple(params))
    
    if tables is not None:
        table_names = [t['TABLE_NAME'] for t in tables]
        
        if table_names:
            selected_table = st.selectbox("Select a Table to Inspect", table_names)
            
            if selected_table:
                st.subheader(f"Schema for `{selected_table}`")
                
                # Fetch columns
                col_query = """
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY, EXTRA 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """
                cols = fetch_data(col_query, (selected_table,))
                if cols:
                    st.dataframe(pd.DataFrame(cols), use_container_width=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Fetch Indexes
                    st.subheader("Indexes & Primary Keys")
                    idx_query = f"SHOW INDEX FROM `{selected_table}`"
                    indexes = fetch_data(idx_query)
                    if indexes:
                        st.dataframe(pd.DataFrame(indexes), use_container_width=True)
                    else:
                        st.info("No indexes found.")
                        
                with col2:
                    # Fetch Foreign Keys
                    st.subheader("Foreign Keys (Relationships)")
                    fk_query = """
                    SELECT 
                        COLUMN_NAME, 
                        REFERENCED_TABLE_NAME, 
                        REFERENCED_COLUMN_NAME 
                    FROM 
                        INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE 
                        TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = %s 
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                    """
                    fks = fetch_data(fk_query, (selected_table,))
                    if fks:
                        st.dataframe(pd.DataFrame(fks), use_container_width=True)
                    else:
                        st.info("No foreign keys found.")
                
                # Preview 5 rows
                st.subheader("Data Preview (First 5 Rows)")
                preview_query = f"SELECT * FROM `{selected_table}` LIMIT 5"
                preview = fetch_data(preview_query)
                
                if preview:
                    st.dataframe(pd.DataFrame(preview), use_container_width=True)
                elif preview == []:
                    st.info("Table is empty.")
                    
        else:
            st.warning("No tables found matching your search.")

elif mode == "Column Search":
    st.header("Column Search")
    st.write("Search for a specific column across all 880+ tables.")
    
    col_kw = st.text_input("Search Columns by Keyword", "")
    
    if col_kw.strip():
        col_query = """
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND COLUMN_NAME LIKE %s
        """
        results = fetch_data(col_query, (f"%{col_kw}%",))
        
        if results:
            st.success(f"Found {len(results)} matches.")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        elif results == []:
            st.warning("No columns match your search keyword.")

elif mode == "Read-Only SQL Console":
    st.header("Read-Only SQL Console")
    st.warning("Write Operations are disabled. Only SELECT, SHOW, DESCRIBE, and EXPLAIN are permitted.")
    
    user_query = st.text_area("Enter your SQL Query here", height=150)
    
    if st.button("Execute Query"):
        if not user_query.strip():
            st.error("Please enter a valid query.")
        else:
            # Basic client-side validation to reject write operations
            allowed_prefixes = ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")
            query_upper = user_query.strip().upper()
            
            # Simple check if the query starts with an allowed keyword
            if not query_upper.startswith(allowed_prefixes):
                st.error("❌ Write operation rejected! Only read queries are allowed in this console.")
                logger.warning(f"Rejected write query attempt: {user_query}")
            else:
                with st.spinner("Executing query..."):
                    result = fetch_data(user_query)
                    
                    if result:
                        st.success(f"Query executed successfully. Returned {len(result)} rows.")
                        st.dataframe(pd.DataFrame(result), use_container_width=True)
                    elif result == []:
                        st.info("Query executed successfully, but returned 0 rows.")
