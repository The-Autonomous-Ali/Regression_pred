from email import header
import sys
from typing import Tuple, List
import numpy as np
from pandas import DataFrame
from sklearn.model_selection import train_test_split
import os

from insurance_structure.entity.config_entity import DataIngestionConfig
from insurance_structure.entity.artifact_entity import DataIngestionArtifact
from insurance_structure.exception import InsurancePriceException
from insurance_structure.logger import logging
from insurance_structure.utils.main_utils import read_yaml_file 
from insurance_structure.data_access.insurance_pred_data import InsuranceData
from insurance_structure.constant.training_pipeline import SCHEMA_FILE_PATH

class DataIngestion:
    def __init__(self, data_ingestion_config: DataIngestionConfig = DataIngestionConfig()):
        """
        :param data_ingestion_config: Configuration for data ingestion
        """
        try:
            self.data_ingestion_config = data_ingestion_config
        except Exception as e:
            raise InsurancePriceException(e, sys)

    def export_data_into_feature_store(self) -> DataFrame:
        try:
            logging.info("Exporting data from MongoDB")
            
            # Instantiate InsuranceData to handle data export
            insurance_data = InsuranceData()
            
            # Export the collection as a DataFrame
            dataframe = insurance_data.export_collection_as_dataframe(
                collection_name=self.data_ingestion_config.collection_name
            )
            
            # Log the database and collection names along with the DataFrame shape
            logging.info(f"Database Name: {insurance_data.mongo_client.database_name}")
            logging.info(f"Collection Name: {self.data_ingestion_config.collection_name}")
            logging.info(f"Shape of DataFrame: {dataframe.shape}")
            
            # Check if the DataFrame is empty
            if dataframe.empty:
                logging.warning("No data found in the collection.")
                return DataFrame()  # Return an empty DataFrame if no data
            
            # Save the exported DataFrame to the specified feature store file path
            feature_store_file_path = self.data_ingestion_config.feature_store_file_path
            dir_path = os.path.dirname(feature_store_file_path)
            os.makedirs(dir_path, exist_ok=True)
            logging.info(f"Saving exported data to feature store file path: {feature_store_file_path}")
            
            # Write DataFrame to CSV
            dataframe.to_csv(feature_store_file_path, index=False, header=True)
            
            return dataframe

        except Exception as e:
            raise InsurancePriceException(e, sys) from e

    def split_data_as_train_test(self, dataframe: DataFrame) -> None:
        """
        Method Name :   split_data_as_train_test
        Description :   This method splits the dataframe into train set and test set based on split ratio 

        Output      :   Folder is created in s3 bucket
        On Failure  :   Write an exception log and then raise an exception
        """
        logging.info("Entered split_data_as_train_test method of Data_Ingestion class")

        try:
            if dataframe.empty:
                raise ValueError("The DataFrame is empty and cannot be split.")

            train_set, test_set = train_test_split(
                dataframe, test_size=self.data_ingestion_config.train_test_split_ratio
            )
            logging.info("Performed train test split on the dataframe")
            logging.info("Exited split_data_as_train_test method of Data_Ingestion class")
            
            dir_path = os.path.dirname(self.data_ingestion_config.training_file_path)
            os.makedirs(dir_path, exist_ok=True)

            logging.info(f"Exporting train and test file path.")
            train_set.to_csv(
                self.data_ingestion_config.training_file_path, index=False, header=True
            )
            test_set.to_csv(
                self.data_ingestion_config.testing_file_path, index=False, header=True
            )

            logging.info(f"Exported train and test file path.")
        except Exception as e:
            raise InsurancePriceException(e, sys) from e

    def initiate_data_ingestion(self) -> DataIngestionArtifact:
        """
        Method Name :   initiate_data_ingestion
        Description :   This method initiates the data ingestion components of the training pipeline 
        
        Output      :   Train set and test set are returned as the artifacts of data ingestion components
        On Failure  :   Write an exception log and then raise an exception
        """
        logging.info("Entered initiate_data_ingestion method of Data_Ingestion class")

        try:
            dataframe = self.export_data_into_feature_store()
            _schema_config = read_yaml_file(file_path=SCHEMA_FILE_PATH)

            dataframe = dataframe.drop(_schema_config["Drop_columns"], axis=1)

            logging.info("Got the data from MongoDB")

            self.split_data_as_train_test(dataframe)

            logging.info("Performed train test split on the dataset")
            logging.info("Exited initiate_data_ingestion method of Data_Ingestion class")

            data_ingestion_artifact = DataIngestionArtifact(
                trained_file_path=self.data_ingestion_config.training_file_path,
                test_file_path=self.data_ingestion_config.testing_file_path,
            )

            logging.info(f"Data ingestion artifact: {data_ingestion_artifact}")
            return data_ingestion_artifact
        except Exception as e:
            raise InsurancePriceException(e, sys) from e
