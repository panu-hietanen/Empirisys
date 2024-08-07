"""
Class to enable accessing Azure tables

Initialised with a specific table name

Author: Panu Hietanen
Date: 06/08/2024
"""

from azure.data.tables import TableServiceClient, TableEntity, UpdateMode
from azure.core.paging import ItemPaged
from azure.core.exceptions import AzureError, ResourceNotFoundError
from typing import Optional, List, Dict, Any, Union
from typing_extensions import Self
import os
import logging
import sys
import csv
import json
from ast import literal_eval

class TableEntry:
    def __init__(self, 
                 partition_key: Optional[str] = None, 
                 row_key: Optional[str] = None, 
                 boost_labels: Optional[List[str]] = None,
                 description: str = '', 
                 manual_labels: Optional[List[str]] = None, 
                 ratings: Optional[Dict[str, str]] = None, 
                 reviewed: bool = False,
                 entry: Optional[Union[TableEntity, Dict[str, Any]]] = None):
        if entry:
            self.PartitionKey = entry['PartitionKey']
            self.RowKey = entry['RowKey']
            self.BoostLabels = entry['BoostLabels']
            self.Description = entry['Description']
            self.ManualLabels = entry['ManualLabels']
            self.Ratings = entry['Ratings']
            self.reviewed = entry['reviewed']
        else:
            self.PartitionKey = partition_key
            self.RowKey = row_key
            self.BoostLabels = json.dumps(boost_labels or [])  # Convert list to JSON string
            self.Description = description
            self.ManualLabels = json.dumps(manual_labels or [])  # Convert list to JSON string
            self.Ratings = json.dumps(ratings or {})  # Convert dictionary to JSON string
            self.reviewed = reviewed

    def __str__(self: Self):
        return str(self.to_dict())

    def to_dict(self: Self) -> Dict[str, Any]:
        return {
            'PartitionKey': self.PartitionKey,
            'RowKey': self.RowKey,
            'BoostLabels': self.BoostLabels,
            'Description': self.Description,
            'ManualLabels': self.ManualLabels,
            'Ratings': self.Ratings,
            'reviewed': self.reviewed
        }

    def data(self: Self) -> Dict[str, Any]:
        return {
            'BoostLabels': self.BoostLabels,
            'Description': self.Description,
            'ManualLabels': self.ManualLabels,
            'Ratings': self.Ratings,
            'reviewed': self.reviewed
        }

class Table:
    """Table class for Azure Table Storage operations."""

    def __init__(self: Self, table_name: str):

        """Initialize the Table class with a specific table name."""
        self.logger = logging.getLogger('azure')
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler(stream=sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        self.table_name = table_name
        self.conn_str = os.getenv("CONNECTION_STRING")
        if not self.conn_str:
            self.logger.error("Connection string not found in environment variables.")
            raise ValueError("Connection string not found")

        try:
            self.service_client = TableServiceClient.from_connection_string(conn_str=self.conn_str)
            self.properties = self.service_client.get_service_properties()
            self.logger.info("TableServiceClient initialized successfully.")
            self.logger.info(f"Table properties: {self.properties}")
        except AzureError as e:
            self.logger.error(f"Error initializing TableServiceClient: {e}")
            raise

        try:
            self.client = self.service_client.get_table_client(table_name=self.table_name)
            self.logger.info(f"Table client for '{self.table_name}' retrieved successfully.")
        except AzureError as e:
            self.logger.error(f"Error getting table client for {self.table_name}: {e}")
            raise

    def create_entity(self: Self, partition: str, row: str, data: Dict[str, Any]) -> None:
        """Create an entity within a table for a given partition and row."""
        new_entity = {
            'PartitionKey': partition,
            'RowKey': row,
            **data,
        }
        try:
            self.client.create_entity(entity=new_entity)
            self.logger.info(f"Entity created in table {self.table_name}.")
        except AzureError as e:
            self.logger.error(f"Error creating entity in table {self.table_name}: {e}")

    def create_entity(self: Self, entity: TableEntry):
        """Create an entity within a table given an existing entity"""
        new_entity = {
            'PartitionKey': entity.PartitionKey,
            'RowKey': entity.RowKey,
            **entity.data(),
        }
        try:
            self.client.create_entity(entity=new_entity)
            self.logger.info(f"Entity created in table {self.table_name}.")
        except AzureError as e:
            self.logger.error(f"Error creating entity in table {self.table_name}: {e}")

    def update_with_dict(self: Self, old: TableEntity, data: Dict[str, Any]) -> None:
        """Update an entity using a dictionary of new data.
        
        Parameters:
        old -- TableEntity, can be returned using `get_entity()`
        data -- Dictionary of new data to be merged
        """
        new_dict = {
            'PartitionKey': old["PartitionKey"],
            'RowKey': old["RowKey"],
            **data,
        }
        self.update(new_dict)

    def update(self: Self, data: Union[TableEntity, Dict[str, Any]]) -> None:
        """Update an entity."""
        try:
            self.client.update_entity(mode=UpdateMode.MERGE, entity=data)
            self.logger.info(f"Successfully updated entity at ({data['PartitionKey']}, {data['RowKey']})")
        except AzureError as e:
            self.logger.error(f"Error updating entity ({data['PartitionKey']}, {data['RowKey']}) in table {self.table_name}: {e}")

    def get_data(self: Self, filters: str = None) -> Optional[ItemPaged[TableEntity]]:
        """Get data that matches filters.
        
        Returns:
        List of dictionaries that match filters, or `None` if error is raised.
        """
        try:
            entities = self.client.query_entities(query_filter=filters)
            self.logger.info(f"Entities retrieved successfully from table {self.table_name}.")
            return list(entities)
        except AzureError as e:
            self.logger.error(f"Error querying entities in table {self.table_name}: {e}")
            return None

    def get_entity(self: Self, partition: str, row: str) -> Optional[TableEntity]:
        """Get data for a given partition and row.
        
        Returns:
        A dictionary corresponding to the given values, or `None` if the partition and key pair don't exist.
        """
        try:
            entity = self.client.get_entity(partition_key=partition, row_key=row)
            self.logger.info(f"Entity retrieved successfully from table {self.table_name}.")
            return entity
        except ResourceNotFoundError:
            self.logger.error(f"Entity at ({partition}, {row}) not found.")
            return None
        except AzureError as e:
            self.logger.error(f"Error getting entity from table {self.table_name}: {e}")
            return None

    def delete_entity(self: Self, partition: str, row: str) -> None:
        """Delete an entity from the table."""
        try:
            self.client.delete_entity(partition_key=partition, row_key=row)
            self.logger.info(f"Entity at ({partition}, {row}) deleted from table {self.table_name}.")
        except AzureError as e:
            self.logger.error(f"Error deleting entity ({partition}, {row}) in table {self.table_name}: {e}")

    def mark_as_reviewed(self: Self, partition: str, row: str) -> None:
        """Mark an observation as reviewed."""
        try:
            entity = self.get_entity(partition, row)
            if entity:
                entity['reviewed'] = True
                self.update(entity)
                self.logger.info(f"Marked entity at ({partition}, {row}) as reviewed.")
            else:
                self.logger.error(f"Entity at ({partition}, {row}) not found.")
        except AzureError as e:
            self.logger.error(f"Error marking entity as reviewed in table {self.table_name}: {e}")

    def to_csv(self: Self, path: str) -> None:
        headers = [
            'PartitionKey',
            'RowKey',
            'BoostLabels',
            'Description',
            'ManualLabels',
            'Ratings',
            'reviewed',
        ]
        try:
            entities = self.get_data()
            if entities:
                with open(path, mode='w', newline='') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=headers)
                    writer.writeheader()
                    for entity in entities:
                        writer.writerow(entity)
            else:
                self.logger.info(f"No entities to write.")
        except Exception as e:
            self.logger.error(f"Error writing to CSV: {e}")
            raise
    
    def import_csv(self: Self, path: str) -> None:
        headers = [
            'PartitionKey',
            'RowKey',
            'BoostLabels',
            'Description',
            'ManualLabels',
            'Ratings',
            'reviewed',
        ]
        try:
            with open(path, mode='r') as csv_file:
                reader = csv.DictReader(csv_file)
                if reader.fieldnames != headers:
                    self.logger.error('Error: CSV headers do not match.')
                    raise Exception('Please provide an appropriately formatted CSV file.')
                for row in reader:
                    entry = TableEntry(entry=row)
                    self.create_entity(entry)
            self.logger.info(f"Entities imported successfully from {path}.")
        except Exception as e:
            self.logger.error(f"Error importing from CSV: {e}")
            raise