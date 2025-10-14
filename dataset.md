

## <a name="dataset"></a>Dataset

### Statistics
| #Train | #Valid | #Test |
|:-------:|:-------:|:-------:|
| 5124 | 1163 | 1167 |


### Data Format

For the task, we have two types of files for each of the train, dev, and test sets: data files (with names like \*_data.json) and label files (with names like \*_label.json). Data files contain the input data for the model, and label files contain the expected model outputs that share the same 'id's as the corresponding data files ([sample data](https://github.com/glee4810/ehrsql-2024/tree/master/sample_data/train)).


#### Input Data (data.json)

```
{
  "version" : dataset version,
	"data" : [
	  {
		  "id" : sample identifier,
			"question" : natural langauge question (either answerable or unanswerable given the MIMIC-IV schema),	
	  },
	...		
	]
}
```

Each object in the data list consists of an ID and the corresponding natural language question.


#### Output Data (label.json)

```
{
  id -> sample identifier : label -> SQL query or 'null' if subject to abstention,
	...
}
```

Each object has a key of a sample's ID and a value of the corresponding label.



##### Table Schema

We follow the same table information style used in [Spider](https://github.com/taoyds/spider). `tables.json` contains the following information for both databases:

- `db_id`: the ID of the database
- `table_names_original`: the original table names stored in the database.
- `table_names`: the cleaned and normalized table names.
- `column_names_original`: the original column names stored in the database. Each column has the format `[0, "id"]`. `0` is the index of the table name in `table_names`. `"id"` is the column name. 
- `column_names`: the cleaned and normalized column names.
- `column_types`: the data type of each column
- `foreign_keys`: the foreign keys in the database. `[7, 2]` indicates the column indices in `column_names`. that correspond to foreign keys in two different tables.
- `primary_keys`: the primary keys in the database. Each number represents the index of `column_names`.


```json
{
    "column_names": [
      [
        -1,
        "*"
      ],      
      [
        0,
        "row id"
      ],
      [
        0,
        "subject id"
      ],
      ...
    ],
    "column_names_original": [
      [
        -1,
        "*"
      ],      
      [
        0,
        "row_id"
      ],
      [
        0,
        "subject_id"
      ],
      ...
    ],
    "column_types": [
      "text",
      "number",
      "number",
      ...
    ],
    "db_id": "mimic_iv",
    "foreign_keys": [
      [
        7,
        2
      ],
      ...
    ],
    "primary_keys": [
      1,
      6,
      ...
    ],
    "table_names": [
      "patients",
      "admissions",
      ...
    ],
    "table_names_original": [
      "patients",
      "admissions",
      ...
    ]
  }
```


### Database

We use the [MIMIC-IV database demo](https://physionet.org/content/mimic-iv-demo/2.2/), which anyone can access the files as long as they conform to the terms of the [Open Data Commons Open Database License v1.0](https://physionet.org/content/mimic-iv-demo/view-license/2.2/). If you agree to the terms, use the bash command below to download the database.

```




