import os
import pandas as pd
import numpy as np
import dart_fss as dart
import OpenDartReader
import tqdm
from utils import load_env, convert_date_format
from datetime import datetime


# 환경 변수 로드
load_env()

# 환경 변수에서 API 키와 데이터 경로 가져오기
DART_API_KEY = os.getenv("DART_API_KEY")
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
# print(DATA_PATH)

# Initialize DART API Key
dart.set_api_key(api_key=DART_API_KEY)
opendartreader = OpenDartReader(DART_API_KEY)

# Load company list from DART
corp_list = dart.get_corp_list()


def corp_info(stock_code, bsns_year):
    """
    Returns the corp_code, bsns_year, and reprt_code for a given stock_code and business year.

    Args:
        stock_code (str): The stock code of the company.
        bsns_year (int): The business year for the report.

    Returns:
        tuple: corp_code, bsns_year, reprt_code if found, otherwise NaN.
    """
    corp = corp_list.find_by_stock_code(stock_code)
    if corp:
        corp_code = corp.corp_code
        reprt_code = 11011  # Report code for business reports
        return str(corp_code), str(bsns_year), str(reprt_code)
    else:
        return np.NaN


def save_report_no(save_path=None, market="kospi"):
    """
    Saves report numbers for each company in the specified market.

    Args:
        PATH (str): Base path for data.
        market (str): Market identifier (e.g., 'kospi').

    Returns:
        str: Path to the saved CSV file containing report numbers.
    """

    if save_path is None:
        save_path = f"{DATA_PATH}/raw"

    df = pd.read_csv(f"{save_path}/{market}/stock_code.csv").head(2)  #### 일부만
    df["stock_code"] = df["stock_code"].apply(lambda x: str(x).zfill(6))
    extracted_data = []

    for stock_code in tqdm.tqdm(df["stock_code"]):
        print(f"Saving Report Info of {stock_code}...")
        try:
            corp = corp_list.find_by_stock_code(stock_code)
            corp_info = corp.load()
            corp_code = corp_info["corp_code"]
            bgn_de = corp_info["est_dt"]
            reports = corp.search_filings(
                bgn_de="20200101",
                # bgn_de=bgn_de,
                end_de="20240801",
                pblntf_ty="A",
                page_no=1,
                page_count=100,
            ).report_list

            extracted_data += [
                {
                    "stock_code": stock_code,
                    "corp_code": item.corp_code,
                    "corp_name": item.corp_name,
                    "report_no": str(item.rcp_no),
                    "report_dt": item.rcept_dt,
                    "report_nm": item.report_nm,
                }
                for item in reports
                if "사업" in item.report_nm
            ]
        except Exception as e:
            print(f"Error in {stock_code}: {e}")

    rcpt_no_df = pd.DataFrame(extracted_data)
    csv_path = f"{save_path}/{market}/보고서코드.csv"
    rcpt_no_df.to_csv(csv_path, index=False)
    print(f"Saved to {csv_path}")
    return


def download_pdf_files(market="kospi"):

    df = pd.read_csv(f"{DATA_PATH}/raw/{market}/보고서코드.csv")

    error_list = []

    df["yy"] = df["report_dt"].apply(convert_date_format)
    df["stock_code"] = df["stock_code"].apply(lambda x: str(x).zfill(6))

    for idx, row in tqdm.tqdm(df.iterrows(), total=df.shape[0]):
        # dart_fss.utils.request.set_delay(1)
        stock_code = row["stock_code"]
        corp_name = row["corp_name"]
        rcp_no = str(row["report_no"])
        yy = row["yy"][:2]
        dir_path = f"{DATA_PATH}/raw/{market}/사업보고서/20{yy}"

        # 디렉토리를 생성
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory '{dir_path}': {e}")

        # 파일 다운로드 및 저장
        try:
            files = opendartreader.attach_files(rcp_no)
            for title, url in files.items():
                if title.endswith(".pdf") and "사업보고서" in title:
                    if "정정" in title:
                        filename = f"[정정]{stock_code}_{corp_name}.pdf"
                    elif "추가" in title:
                        filename = f"[추가]{stock_code}_{corp_name}.pdf"
                    else:
                        filename = f"{stock_code}_{corp_name}.pdf"

                    file_path = os.path.join(dir_path, filename)
                    print(f"Downloading {title} from {url} to {file_path}")
                    opendartreader.download(url, file_path)
        except Exception as e:

            print(f"Error downloading files for report number '{rcp_no}': {e}")
            error_list.append(f"{stock_code}_{corp_name}_{rcp_no}")

    error_file_path = f"{DATA_PATH}/processed/[{market}]report_download_error_list.txt"
    with open(error_file_path, "w") as f:
        for error in error_list:
            f.write(f"{error}\n")
    print(f"Error list saved to {error_file_path}")


def download_jungwan(market="kospi", output_dir=None):
    """
    Downloads the 정관 첨부파일 for a given market.
    """
    if output_dir is None:
        output_dir = f"{DATA_PATH}/raw/{market}/정관"

    reports_df = pd.read_csv(f"{DATA_PATH}/raw/{market}/보고서코드.csv").head(5)
    reports_df = reports_df[["stock_code", "corp_name", "report_no"]]
    reports_df["stock_code"] = reports_df["stock_code"].apply(lambda x: str(x).zfill(6))

    # print(df)
    # Iterate through each row in the DataFrame
    for index, row in reports_df.iterrows():
        stock_code = row["stock_code"]
        corp_name = row["corp_name"]
        report_no = row["report_no"]

        reports = corp_list.find_by_stock_code(stock_code).search_filings(
            bgn_de="20200101", pblntf_detail_ty="a001"
        )
        r = reports[0]
        found_pages = r.find_all(
            includes=r"정\s*관", excludes=r"사항"
        )  # 사업보고서 내부 페이지 검색 ("정관" 포함, "사항" 미포함)
        result = found_pages["attached_reports"][0].html  # 정관페이지의 HTML 값

        SAVE_ZIP_PATH = f"{output_dir}/{stock_code}_{corp_name}.html"
        with open(SAVE_ZIP_PATH, "w") as file:
            file.write(str(result))  # HTML 파일롤 저장

        dart.api.filings.download_document(SAVE_ZIP_PATH, report_no)

    return 1


#### xml 형태로 된 보고서 다운 > txt 파일로 변환
'''
def download_xml_report(market="kospi"):
    """
    Downloads and unzips the business reports for a given market.

    Args:
        market (str): Market identifier (e.g., 'kospi').

    Returns:
        int: 1 on success.
    """
    SAVE_DIR = f"{DATA_PATH}/report/{market}/xml"
    reports_df = pd.read_csv(f"{DATA_PATH}/metadata/{market}/report_no.csv")
    reports_df["stock_code"] = reports_df["stock_code"].apply(lambda x: str(x).zfill(6))

    for index, row in reports_df.iterrows():
        stock_code = row["stock_code"]
        corp_name = row["corp_name"]
        report_no = row["report_no"]
        SAVE_ZIP_PATH = f"{SAVE_DIR}/{stock_code}_{corp_name}/zip"
        dart.api.filings.download_document(SAVE_ZIP_PATH, report_no)
    return 1

def unzip_all_files(zip_dir, unzip_dir):
    """
    Unzips all files in a given directory.

    Args:
        zip_dir (str): Path to the directory containing zip files.
        target_dir (str): Path to the directory where files will be extracted.
    """
    os.makedirs(unzip_dir, exist_ok=True)
    zip_files = [f for f in os.listdir(zip_dir) if f.endswith(".zip")]

    for zip_file in zip_files:
        zip_path = os.path.join(zip_dir, zip_file)
        with ZipFile(zip_path, "r") as zipObj:
            zipObj.extractall(unzip_dir)
            print(f"Extracted {zip_file} into {unzip_dir}")

def xml_to_txt(xml_dir, txt_dir):
    """
    Converts XML business reports to text files for a given training or test dataset.
    """
    xml_files = [f for f in os.listdir(xml_dir) if f.endswith(".xml")]
    utf_error = []

    for xml_file in xml_files:
        xml = open(os.path.join(xml_dir, xml_file), "rt", encoding="utf8")
        txt = open(os.path.join(txt_dir, xml_file[:-4] + ".txt"), "wt")
        try:
            txt.write(xml.read())
        except:
            utf_error.append(xml_file)
            continue

    for xml_file in utf_error:
        xml = open(os.path.join(xml_dir, xml_file), "rt", encoding="euc-kr")
        txt = open(os.path.join(txt_dir, xml_file[:-4] + ".txt"), "wt")
        try:
            txt.write(xml.read())
        except:
            print(f"Translation Error : {xml_file}")
            continue

def process_report(market="kospi"):
    """
    Processes reports by unzipping and converting them to text files.

    Args:
        market (str): Market identifier (e.g., 'kospi').
    """
    df = pd.read_csv(f"{DATA_PATH}/metadata/{market}/stock_code.csv")
    df["stock_code"] = df["stock_code"].apply(lambda x: str(x).zfill(6))

    for _, row in df.iterrows():
        stock_code = row.stock_code
        co_nm = row.co_nm
        target_dir_xml = f"{DATA_PATH}/report/{market}/xml/{stock_code}_{co_nm}"
        zip_dir = f"{target_dir_xml}/zip"
        print(f"Unzip : {zip_dir} to {target_dir_xml} ...")
        unzip_all_files(zip_dir, target_dir_xml)

        target_dir_txt = f"{DATA_PATH}/report/{market}/txt/{stock_code}_{co_nm}"
        xml_to_txt(target_dir_xml, target_dir_txt)

'''
