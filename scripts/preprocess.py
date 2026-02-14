import pandas as pd
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(BASE_DIR, "data", "Dönem 3 Bahar Dönemi .xlsx") 
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "clean_data.csv") 

data = pd.read_excel(EXCEL_PATH,sheet_name=None,header=None)

except_sheets = ["SINAV","GÖZLEM","SORUMLU","TATİL"]
clean_data = []

def normalize_name(text):

    if not isinstance(text, str) or text.lower() == 'nan':
        return None, "Belirsiz"

    first_row = text.split("\n")[0].strip()
    clean_text = re.split(r'\s{2,}',first_row)[0].strip()

    committee_match = re.search(r'(KOMİTE|COMMITTEE)\s*[-]*\s*(\d+)', clean_text, re.IGNORECASE)
    committee_num = int(committee_match.group(2)) if committee_match else None 

    if "PANEL:" in clean_text.upper():
        committee_num = 5 
        if "/" in clean_text:
            lecture_name = clean_text.split('/')[-1].strip()
        else:
            lecture_name = clean_text
    
    elif committee_num is not None:
        lecture_name = re.sub(r'(KOMİTE|COMMITTEE)\s*[-]*\s*\d+\s*/\s*', '', clean_text, flags=re.IGNORECASE).strip()

    else:
        lecture_name = clean_text

    lecture_name = re.sub(r'\((P|p)$', '(P)', lecture_name)
    lecture_name = re.sub(r'\((T|t)$', '(T)', lecture_name)

    return committee_num,lecture_name

def normalize_lecture_name(lecture_name,lecture_type):

    lecture_name = lecture_name.strip()

    if lecture_type == "Pratik":
        if not re.search(r'\([Pp]\)?$', lecture_name):
            lecture_name = f"{lecture_name} (P)"
        
        else:
            lecture_name = re.sub(r'\([Pp]\)?$', '(P)', lecture_name)

    return lecture_name

for sheet_name,df in data.items():

    if any(keyword in sheet_name.upper() for keyword in except_sheets):
        continue

    print(f"--- {sheet_name} işleniyor ---")


    date_pattern = r'\d{4}-\d{2}-\d{2}'

    date_row_index = -1
    date_columns = {}

    for i in range(len(df)):

        row_text = "".join(map(str,df.iloc[i]))

        if(re.search(date_pattern,row_text)):
            date_row_index = i

            for column_index, block in enumerate(df.iloc[i]):
                isdate = re.search(date_pattern, str(block))

                if isdate:
                    extracted_date = isdate.group()
            
            
                    if "2024-02-11" in extracted_date:
                        extracted_date = extracted_date.replace("2024", "2026")
                
                    date_columns[column_index] = extracted_date



    clock_pattern = r'\d{2}:\d{2}-\d{2}:\d{2}'
    
    last_lecture_memory = {col_idx: None for col_idx in date_columns.keys()}

    for i in range(date_row_index + 1, len(df)):
        clock_block = str(df.iloc[i, 0]).strip()

        if re.search(clock_pattern, clock_block):
            
            row_vals = [str(val).lower().strip() for val in df.iloc[i, list(date_columns.keys())]]
            is_break_row = all(val == 'nan' or val == '' or 'öğle' in val for val in row_vals)

            if is_break_row:
                
                for col in last_lecture_memory:
                    last_lecture_memory[col] = None
                continue 

            for column_index, date in date_columns.items():
                if column_index > 6:
                    continue

                content = str(df.iloc[i, column_index]).strip()

                
                if content != 'nan' and content != '':
                    if 'Öğle Arası' in content.lower():
                        last_lecture_memory[column_index] = None
                    else:
                        last_lecture_memory[column_index] = content
                else:
                    
                    pass
                
                current_lecture = last_lecture_memory[column_index]
                
                
                
                if current_lecture:

                    committee, lecture = normalize_name(current_lecture)
                    
                    lecture_type = "Pratik" if re.search(r'\(P\)|LAB|PRATİK|FANTOM', current_lecture.upper()) else "Teorik"

                    lecture = normalize_lecture_name(lecture,lecture_type)
                    
                    clean_data.append({
                        "Date": date,
                        "Time": clock_block,
                        "Committee": committee,
                        "Lecture": lecture,
                        "Type": lecture_type 
                    })

clean = pd.DataFrame(clean_data)
print(clean.head(10))

clean.to_csv(OUTPUT_PATH,index=None)