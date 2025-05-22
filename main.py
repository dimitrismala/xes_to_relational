import pandas as pd
import mysql.connector
import uuid
from sqlalchemy import create_engine, MetaData
from pm4py.objects.log.importer.xes import importer as xes_importer
from pathlib import Path
from datetime import datetime
from tqdm import tqdm


def batch_insert_data(df, table_name, engine, chunk_size=500):
    for i in range(0, len(df), chunk_size):
        chunk = df[i:i + chunk_size]
        chunk.to_sql(name=table_name, con=engine, index=False, if_exists='append')


def infer_datatype(attr_value):
    if isinstance(attr_value, bool):
        return 'boolean'
    elif isinstance(attr_value, int):
        return 'int'
    elif isinstance(attr_value, float):
        return 'float'
    elif isinstance(attr_value, datetime):
        return 'date'
    elif isinstance(attr_value, str):
        # Try to parse the value as a UUID
        try:
            uuid.UUID(attr_value)
            return 'id'
        except ValueError:
            return 'string'
    elif isinstance(attr_value, dict):
        if attr_value["value"] is None:
            return 'list'
        else:
            return infer_datatype(attr_value["value"])
    else:
        return 'unknown'


def get_attr_data(attributes, attribute_value, data_extension, parent_id=None):
    data = []
    for attr_key, attr_value in attributes.items():
        attr_id = str(uuid.uuid4())  # Use UUID as ID

        datatype = infer_datatype(attr_value)
        ext_id = process_extension_block(attr_key, data_extension)

        attr_row = {'id': attr_id, 'attr_key': attr_key, 'attr_type': datatype, 'parent_id': parent_id,
                    'extension_id': ext_id}

        if isinstance(attr_value, dict):
            data.append(attr_row)
            if attr_value["value"] is not None:
                attribute_value.append(attr_value["value"])
            else:
                attribute_value.append(None)

            for child_key, child_value in attr_value['children'].items():
                data.extend(get_attr_data({child_key: child_value}, attribute_value, data_extension, attr_id))
        else:
            data.append(attr_row)
            attribute_value.append(attr_value)

    return data


def process_extension_block(attr_key, extensions_data):
    if attr_key is None or extensions_data is None:
        return None

    for ext in extensions_data:
        prefix = ext.get("prefix", "") + ':'
        if prefix in attr_key:
            return ext["id"]
    return None


xes_file_path = 'BPI_Challenge_2019.xes'

# Check if the file exists
if not Path(xes_file_path).is_file():
    print(f"Error: XES file '{xes_file_path}' not found. Please provide the correct file path.")
    exit()  # Exit the script or handle the error appropriately

# Import the XES log
print("Importing the XES file...")
log = xes_importer.apply(xes_file_path)
print("XES file imported successfully!\n")

log_id = str(uuid.uuid4())  # Use UUID as ID
xes_name = Path(xes_file_path).stem  # Log file name

# MySQL database connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'bigtest'
}

# Establish a connection to the MySQL server using mysql-connector-python
connection = mysql.connector.connect(**db_config)

try:
    # Create an SQLAlchemy engine using the connection
    engine = create_engine(
        f"mysql+mysqlconnector://{db_config['user']}:"
        f"{db_config['password']}@{db_config['host']}/{db_config['database']}")

    # Define metadata and create a connection
    metadata = MetaData()

    # Insert a single row into the 'log' table
    with connection.cursor() as mycursor:
        sql = "INSERT INTO log (id, name) VALUES (%s, %s)"
        val = (log_id, xes_name)
        mycursor.execute(sql, val)

    connection.commit()

    data_classifier = []

    if hasattr(log, 'classifiers'):
        classifiers = log.classifiers

        for classifier_name, classifier_value in classifiers.items():
            classifier_id = str(uuid.uuid4())  # Use UUID as ID
            classifier_keys = ""

            for key in classifier_value:
                classifier_keys += key + " "

            classifier_keys = classifier_keys[:-1]  # Remove the space character in the end

            row = {'id': classifier_id, 'name': classifier_name, 'attr_keys': classifier_keys, 'log_id': log_id}

            data_classifier.append(row)

        df_classifiers = pd.DataFrame(data_classifier)
        df_classifiers.to_sql(name='classifier', con=engine, index=False, if_exists='append')
        del data_classifier
        del df_classifiers

    data_extension = []
    prefix_names = []

    # Accessing global extensions dynamically
    if hasattr(log, 'extensions'):
        extensions = log.extensions
        for extension_name, extension_value in extensions.items():
            extension_id = str(uuid.uuid4())  # Use UUID as ID

            row = {'id': extension_id, 'name': extension_name, 'prefix': extensions[extension_name]["prefix"],
                   'uri': extensions[extension_name]["uri"]}

            data_extension.append(row)

        df_extensions = pd.DataFrame(data_extension)
        df_extensions.to_sql(name='extension', con=engine, index=False, if_exists='append')
        del df_extensions

    for extension in data_extension:
        prefix_names.append(extension["prefix"])

    attribute_value, data_log_has_attribute, data_attribute = [], [], []

    # Log's global attributes
    temp_data = get_attr_data(log.attributes, attribute_value, data_extension)
    data_attribute.extend(temp_data)

    for i, attribute in enumerate(temp_data):
        row = {'log_id': log_id, 'trace_global': 0, 'event_global': 0, 'attribute_id': attribute['id'],
               'value': attribute_value[i]}
        data_log_has_attribute.append(row)

    attribute_value = []

    # Log's trace global scope attributes
    if bool(log.omni_present):  # check if log.omni_present dictionary is empty
        temp_data = get_attr_data(log.omni_present['trace'], attribute_value, data_extension)
        data_attribute.extend(temp_data)

        for i, attribute in enumerate(temp_data):
            row = {'log_id': log_id, 'trace_global': 1, 'event_global': 0, 'attribute_id': attribute['id'],
                   'value': attribute_value[i]}
            data_log_has_attribute.append(row)

        attribute_value = []

        # Log's event global scope attributes
        temp_data = get_attr_data(log.omni_present['event'], attribute_value, data_extension)
        data_attribute.extend(temp_data)

        for i, attribute in enumerate(temp_data):
            row = {'log_id': log_id, 'trace_global': 0, 'event_global': 1, 'attribute_id': attribute['id'],
                   'value': attribute_value[i]}
            data_log_has_attribute.append(row)

    # Insert log's attributes
    df_attribute = pd.DataFrame(data_attribute)
    data_attribute = []

    try:
        batch_insert_data(df_attribute, 'attribute', engine, chunk_size=2000)
        connection.commit()
    except Exception as e:
        print(f"Batch failed: {e}")
        connection.rollback()

    del df_attribute

    df_log_has_attribute = pd.DataFrame(data_log_has_attribute)
    del data_log_has_attribute

    try:
        batch_insert_data(df_log_has_attribute, 'log_has_attribute', engine, chunk_size=2000)
        connection.commit()
    except Exception as e:
        print(f"Batch failed: {e}")
        connection.rollback()

    del df_log_has_attribute

    data_log_has_trace = []
    data_trace, data_trace_has_attribute, data_event_has_attribute = [], [], []
    trace_id, event_id = None, None

    for trace in tqdm(log, desc="Processing traces", unit=" trace"):
        trace_id = str(uuid.uuid4())  # Use UUID as ID

        # Insert a single row into the 'trace' table
        with connection.cursor() as mycursor:
            sql = "INSERT INTO trace (id) VALUES (%s)"
            val = (trace_id,)
            mycursor.execute(sql, val)

        connection.commit()

        row = {'log_id': log_id, 'trace_id': trace_id}
        data_log_has_trace.append(row)

        attribute_value = []

        temp_data = get_attr_data(trace.attributes, attribute_value, data_extension)
        data_attribute.extend(temp_data)

        df_attribute = pd.DataFrame(data_attribute)
        data_attribute = []

        try:
            batch_insert_data(df_attribute, 'attribute', engine, chunk_size=2000)
            connection.commit()
        except Exception as e:
            print(f"Batch failed: {e}")
            connection.rollback()

        del df_attribute

        for i, attribute in enumerate(temp_data):
            row = {"trace_id": trace_id, "attribute_id": attribute["id"], "value": attribute_value[i]}
            data_trace_has_attribute.append(row)

        data_event, data_trace_has_event = [], []

        for event in trace:
            event_id = str(uuid.uuid4())  # Use UUID as ID

            data_event.append({'id': event_id})

            row = {'trace_id': trace_id, 'event_id': event_id}
            data_trace_has_event.append(row)

            attribute_value = []

            temp_data = get_attr_data(event, attribute_value, data_extension)
            data_attribute.extend(temp_data)

            for i, attribute in enumerate(temp_data):
                row = {"event_id": event_id, "attribute_id": attribute["id"], "value": attribute_value[i]}
                data_event_has_attribute.append(row)

        df_attribute = pd.DataFrame(data_attribute)
        data_attribute = []

        try:
            batch_insert_data(df_attribute, 'attribute', engine, chunk_size=2000)
            connection.commit()
        except Exception as e:
            print(f"Batch failed: {e}")
            connection.rollback()

        del df_attribute

        df_event = pd.DataFrame(data_event)

        try:
            batch_insert_data(df_event, 'event', engine, chunk_size=2000)
            connection.commit()
        except Exception as e:
            print(f"Batch failed: {e}")
            connection.rollback()

        del df_event

        df_event_has_attribute = pd.DataFrame(data_event_has_attribute)
        data_event_has_attribute = []

        try:
            batch_insert_data(df_event_has_attribute, 'event_has_attribute', engine, chunk_size=2000)
            connection.commit()
        except Exception as e:
            print(f"Batch failed: {e}")
            connection.rollback()

        del df_event_has_attribute

        df_trace_has_event = pd.DataFrame(data_trace_has_event)
        del data_trace_has_event

        try:
            batch_insert_data(df_trace_has_event, 'trace_has_event', engine, chunk_size=2000)
            connection.commit()
        except Exception as e:
            print(f"Batch failed: {e}")
            connection.rollback()

        del df_trace_has_event

        pass

    df_log_has_trace = pd.DataFrame(data_log_has_trace)
    del data_log_has_trace
    df_log_has_trace.to_sql(name='log_has_trace', con=engine, index=False, if_exists='append')
    del df_log_has_trace

    df_trace_has_attribute = pd.DataFrame(data_trace_has_attribute)

    try:
        batch_insert_data(df_trace_has_attribute, 'trace_has_attribute', engine, chunk_size=2000)
        connection.commit()
    except Exception as e:
        print(f"Batch failed: {e}")
        connection.rollback()

    # Update the sequence column in the log_has_trace and trace_has_event tables
    with connection.cursor() as mycursor:
        sql = """
        UPDATE log_has_trace AS lt
        JOIN (
            SELECT ta.trace_id, COUNT(*) AS sequence
            FROM trace_has_attribute AS ta
            JOIN attribute AS a ON ta.attribute_id = a.id
            JOIN trace AS t ON ta.trace_id = t.id
            JOIN log_has_trace AS lt2 ON t.id = lt2.trace_id
            WHERE a.attr_key = 'concept:name' AND lt2.log_id = (%s)
            GROUP BY ta.value
        ) AS counts ON lt.trace_id = counts.trace_id
        SET lt.sequence = counts.sequence;
        """

        val = (log_id,)
        mycursor.execute(sql, val)

        sql = """
        UPDATE trace_has_event AS the
        JOIN (
            SELECT te.event_id, COUNT(*) AS sequence
            FROM event_has_attribute AS ea
            JOIN attribute AS a ON ea.attribute_id = a.id
            JOIN trace_has_event AS te ON ea.event_id = te.event_id
            JOIN trace AS t ON te.trace_id = t.id
            JOIN log_has_trace AS lt ON t.id = lt.trace_id
            WHERE a.attr_key = 'concept:name' AND lt.log_id = (%s)
            GROUP BY ea.value
        ) AS counts ON the.event_id = counts.event_id
        SET the.sequence = counts.sequence;
        """

        mycursor.execute(sql, val)

    connection.commit()

except Exception as e:
    print(f'Error: {e}')
    connection.rollback()  # Rollback the transaction in case of an exception

finally:
    # Close the database connection
    connection.close()
