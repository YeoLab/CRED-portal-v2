# README

## Things that need to be added/modified when adding a new:


#### Overview:
- views.submit_job_view() pulls from a list of tools (tools.valid_pipelines()) as a dictionary of {keys:Objects}, with each Object a class of tool (ie. Job).
- set_my_files() will take a GET request and return a list of files that the user should have selected for processing (Select files button)
- Using the above dictionary of tools, submit_job_view() will build a DynamicForm whose fields correspond to each tool. The DynamicForm constructor takes in three arguments:
    - dynamic_fields: Job.get_form_options(json_payload=None)  # ignore json_payload, this is a WIP feature that allows users to resubmit jobs
    - user: string representation of user (username)
    - my_files: list of files
- Each new tool should have a 'get_form_options()' method, which defines the structure, options, defaults, and restrictions for each field of the tool.
    - The structure may include lists, sets, tuples of any type, so it may be complex. 
    - The dictionary returned by get_form_objects() may include one or more of these keys defined in DynamicForm:
    (e.g. "file_inputs", "text_inputs", "date_inputs", "textarea_inputs", "integer_inputs", "dropdown_inputs"). 
    ### The keys and format of get_form_options() MUST match those expected by DynamicForm().
#### Sequencing tool:
- u19_ncrcrg/tools.py: 
    - New tools extend the Job class, which defines
        - get_default_options(): Returns an OrderedDict that defines 'experiment-level' metadata, such as: 
            - module: Name of the module on TSCC (eg. "cellranger")
            - module_version: Version of the module on TSCC (eg. "3.0.2")
            - module_script: bash script that wraps the cwl or wdl runner command (eg. cellranger-3.0.2-runner, typically found at $MODULE_HOME/wf)
            - experiment_nickname: also known as the job name that the user will see
            - project: should a user wish to group experiments (jobs) together, he/she may tag a project
            - processing_date: the current date and time of submission
            - job_summary: description of the job
        - generate_default_job_submission_document(): Collects Object attributes and returns a dictionary to be appended to the final submissino document.
    - Tools not included within the CReD portal (but should be linked to external resources) may extend ExternalTool()