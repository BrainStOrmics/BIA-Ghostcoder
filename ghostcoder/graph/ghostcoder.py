from ghostcoder.utils import *
from ghostcoder.prompts import load_prompt_template
from .coder import create_coder_agent
from .retriever import create_retriever_agent
from .filemanager import create_filemanager_agent
from ..config import *

from typing import TypedDict, Optional, Type, Any
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.pregel import RetryPolicy


def create_ghostcoder_agent(
    chat_model: LanguageModelLike,
    reason_model: LanguageModelLike,
    code_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "ghostcoder",
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    store: Optional[BaseStore] = None,
    interrupt_before: Optional[list[str]] = None,
    interrupt_after: Optional[list[str]] = None,
    debug: bool = False,
    ) -> CompiledStateGraph:

    #----------------
    # TODO: Optimize agent framework
    #----------------6

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        task_description: str
        previous_codeblock: str # optional, default use none
        task_id: str # optional, default use ghostcoder_config.TASK_ID
        session_id: str # optional, default use ghostcoder_config.SESSION_ID
        
        #parameters 
        n_iter: int
        max_iter: int 
        #generated
        task_instruction: str # node_task_parser
        criteria: str # node_task_parser
        data_files: list # node_filemanager
        env_profiles: dict # node_filemanager
        ref_codeblocks: str # node_retriever
        generated_codeblock_4dp: str # node_data_perception_coder
        data_perception: str # node_data_perception_coder
        generated_codeblock: str # node_task_coder
        execution_outstr: str # node_task_coder
        eval_decision: bool # node_evaluator
        improvements: str # node_evaluator
        #task_result: str

        #debug
        retriever_state:dict
        dp_coder_state:dict
        coder_state:dict


    #----------------
    # Load subgraphs
    #----------------

    # Get crawler subgraph 
    coder_subgraph = create_coder_agent(
        chat_model = chat_model, 
        reason_model = reason_model,
        code_model = code_model,
        max_retry = max_retry,
        name =  "coder_subgraph",
        config_schema = config_schema,
        checkpointer = checkpointer,
        store = store,
        interrupt_before = interrupt_before,
        interrupt_after = interrupt_after,
        debug = debug,
        )

    retriever_subgraph = create_retriever_agent(
        chat_model = chat_model, 
        max_retry = max_retry,
        name =  "retriever_subgraph",
        config_schema = config_schema,
        checkpointer = checkpointer,
        store = store,
        interrupt_before = interrupt_before,
        interrupt_after = interrupt_after,
        debug = debug,
        )
    
    filemanager_subgraph = create_filemanager_agent(
        name =  "filemanager_subgraph",
        config_schema = config_schema,
        checkpointer = checkpointer,
        store = store,
        interrupt_before = interrupt_before,
        interrupt_after = interrupt_after,
        debug = debug,
        )
    
    

    #----------------
    # Define nodes
    #----------------

    async def node_filemanager(state:State):
        """"""

        # Pass and update inputs
        try:
            task_id = state['task_id']
            ghostcoder_config.TASK_ID = task_id
        except:
            task_id = ghostcoder_config.TASK_ID
        try:
            session_id = state['session_id']
        except:
            session_id = ghostcoder_config.SESSION_ID
            ghostcoder_config.SESSION_ID = session_id

        docker_profile_dir = docker_config.DOCKER_PROFILES_DIR

        # Parse subgraph inputs
        fm_input = {
            "task_id": task_id,
            "session_id": session_id,
            "max_iter": file_config.MAX_ITER,
        }
        
        # Get reference using file manager subgraph
        i = 0
        while i < max_retry:
            try:
                filemanager_state = await filemanager_subgraph.ainvoke(
                    fm_input,
                    config = config_schema)
                # Pass output
                data_files = filemanager_state['data_files']
                env_profiles = filemanager_state['env_profiles']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error deal with file system due to: {e}")
                    raise  
        
        # Return 
        return {
            "data_files": data_files,
            "env_profiles": env_profiles,
            "filemanager_state": filemanager_state,
            "n_iter" : 0,
        }

    def node_task_parser(state:State):
        """"""

        # Pass inputs
        task_description = state['task_description']
        data_perception = state['data_perception']
        previous_codeblock = state['previous_codeblock']
        n_iter = state['n_iter']
        try:
            improvements = state['improvements']
            task_instruction = state['task_instruction']
            execution_outstr = state['execution_outstr']
            generated_codeblock = state['generated_codeblock']
        except:
            improvements = ""


        # Parse human input
        human_input = ""
        if len(improvements) > 1:
            human_input += "## Critique for previous round of code generation and execution  \nYou have provided the user with a one-time task instruction, as follow:\n" + task_instruction + "\n"
            human_input += "### Improvements  \nThe improvements suggested by the users are:\n" + improvements + "\n"
            human_input += "### Results  \nAnd the following is the execution result of the code generated by this instruction:\n" + execution_outstr + "\n" 
            human_input += "### Code  \nAbove results were produced by the following code:\n" + generated_codeblock + "\n"
        if len(previous_codeblock) > 1:
            human_input += "## Codes for previous step:  \n---------\n" + previous_codeblock + '\n---------\n'

        # Call prompt template
        prompt, input_vars = load_prompt_template('ghostcoder.task_parse')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(task_description = task_description)),
            HumanMessage(content=human_input)
        ]

        # Generate task instruction with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry:
            try:
                json_output = chain.invoke(message)
                task_instruction =  json_output['instruction']
                criteria = json_output['criteria']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating task instruction: {e}")
                    raise  

        return {
            "task_instruction": task_instruction,
            "criteria": criteria,
            }


    def node_retriever(state:State):
        """"""
        # Pass inputs
        retriever_input = {
            "task_description": state['task_description']
            }
        
        if ghostcoder_config.DB_RETRIEVE:
            # Get reference using Retriever subgraph
            i = 0
            while i < max_retry:
                try:
                    retriever_state = retriever_subgraph.invoke(
                        retriever_input,
                        config = config_schema)
                    # Pass output
                    ref_codeblocks = retriever_state['ref_codeblocks']
                    break
                except Exception as e:
                    i+=1
                    if i == max_retry:
                        print(f"Error get reference code due to: {e}")
                        raise  
        else:
            ref_codeblocks = ""
            retriever_state = {}

        return {
            "ref_codeblocks":ref_codeblocks,
            "retriever_state":retriever_state,
            }
    
    async def node_data_perception_coder(state:State):
        """"""
        dp_instruction = """
### **Actions & Tools**
The method for inspecting the file is determined by its type and context. Follow these rules in order of priority:

1.  **For Large-Scale Bioinformatics Files (e.g., `.fastq`, `.fq.gz`, `.bam`, `.sam`):**
    -   **Action:** Do not attempt to read or load the file content. These files are typically too large for simple inspection.
    -   **Code:** Write a simple script that **prints the provided filename** to standard output to confirm its presence and acknowledge it as an input.

2.  **For R-Native Data Files (e.g., `.rds`, `.rda`, `.rdata`):**
    -   **Action:** You **must** use the `R` language.
    -   **Code:** Use `readRDS()` (for `.rds`) or `load()` (for `.rda`/`.rdata`) to import the data, then use the `str()` function to print a detailed summary of the primary object's structure.

3.  **For Python-Native or HDF5-Based Files (e.g., `.h5ad`, `.pkl`, `.h5`):**
    -   **Action:** You **must** use the `Python` language.
    -   **Code:** Use the appropriate specialized library to load the object (`anndata`/`scanpy` for `.h5ad`, `pickle` for `.pkl`, `h5py` for generic `.h5`). Print the loaded object itself to display its default summary.

4.  **For Generic Tabular/Text Files (e.g., `.csv`, `.tsv`, `.txt`):**
    -   **Action:** The language choice depends on the context of other files in the analysis.
        -   **If accompanied by R-native files (`.rds`/`.rda`):** Use `R`. Load the data (e.g., with `read.csv()`) and inspect it with `str()` and `head()` for consistency.
        -   **If accompanied by Python-native files (`.h5ad`/`.pkl`):** Use `Python` with the `pandas` library. Load the data and inspect it with `.info()` and `.head()` for consistency.
        -   **If no other files are present (standalone case):** Default to using `Python` with `pandas`. Load the data and inspect it with `.info()` and `.head()`.

### **Expected Output**
-   The code should not create or save any new files.
-   The entire output should be the requested metadata printed to standard output (stdout).
-   The stdout must contain the relevant structural information (or just the filename for large files) as determined by the rules above.
"""

        # Pass inputs
        data_files = state['data_files']

        # Parse data perception task
        task_instruction = "### Purpose\nTo inspect a given data file to understand its structure, format, and content (metadata) before performing any analysis. This helps prevent errors and inform the next steps of the workflow. The choice of tool and language will be adapted based on the file type and the context of other available data.:\n - Data files:" + str(data_files) + "\n"
        task_instruction += dp_instruction
        
        data_perception =  "Your mission is to precept data based on data files names."

        # Pass subgraph inputs
        coder_input = {
            "task_instruction"  : task_instruction,
            "data_perception"   : data_perception,
            "ref_codeblocks"    : "",
            "previous_codeblock": "",
            }

        if ghostcoder_config.ALLOW_DATA_PERCEPTION:
            # Generate bioinformatics code with coder subgraph
            coder_state = await coder_subgraph.ainvoke(
                coder_input,
                config = config_schema
                )

            # Pass output
            generated_codeblock = coder_state['generated_codeblock'][-1]
            execution_outstr = coder_state['execution_outstr']
        else:
            generated_codeblock = ""
            execution_outstr = "Data perception is not available."
            coder_state = {}

        # Return 
        return {
            "generated_codeblock_4dp":generated_codeblock,
            "data_perception": execution_outstr,
            "dp_coder_state":coder_state
            }

    async def node_task_coder(state:State):
        """"""
        # Parse subgraph input 
        task_instruction = state['task_instruction']
        data_perception = state['data_perception']

        # Pass inputs
        coder_input = {
            "task_instruction"  :task_instruction,
            "data_perception"   :data_perception,
            "ref_codeblocks"    : state['ref_codeblocks'],
            "previous_codeblock": state['previous_codeblock'],
            "env_profiles"      : state["env_profiles"],
            }

        # Generate bioinformatics code with coder subgraph
        coder_state = await coder_subgraph.ainvoke(
            coder_input,
            config = config_schema
            )

        # Pass output
        generated_codeblock = coder_state['generated_codeblock'][-1]
        execution_outstr = coder_state['execution_outstr']
        
        return {
            "generated_codeblock":generated_codeblock,
            "execution_outstr": execution_outstr,
            "coder_state":coder_state
            }


    def node_evaluator(state:State):
        """"""

        # Pass inputs
        task_description = state['task_description']
        task_instruction = state['task_instruction']
        generated_codeblock = state['generated_codeblock']
        execution_outstr = state['execution_outstr']
        criteria = state['criteria']

        human_input = "## Instruction in last round:  \n" + task_instruction + '\n'
        human_input += "## Evaluation criteria:  \n" + criteria + '\n'
        human_input += "## Execution results:  \n" + execution_outstr + '\n'
        human_input += "## Produced by following code:  \n" + generated_codeblock + '\n'

        # Call prompt template
        prompt, input_vars = load_prompt_template('ghostcoder.eval')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(task_description=task_description)),
            HumanMessage(content=human_input)
        ]

        # Generate task instruction with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry:
            try:
                json_output = chain.invoke(message)
                eval_decision =  json_output['decision']
                improvements = json_output['improvements']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating task instruction: {e}")
                    raise  

        # update iteration 
        n_iter += 1
        
        return {
            "eval_decision": eval_decision, 
            "improvements": improvements,
            "n_iter": n_iter,
        }
    

    # def node_output_parser(state:State):
    #     """"""

    #     # Pass inputs
    #     task_instruction = state['task_instruction']
    #     generated_codeblock = state['generated_codeblock'][-1]
    #     execution_outstr = state['execution_outstr']

    #     # Parse human input
    #     human_input =  "## Instruction of analysis task:  \n" + task_instruction + '\n'
    #     human_input += "## Execution by following code:  \n" + generated_codeblock + '\n'
    #     human_input += "## Execution results:  \n" + execution_outstr + '\n'

    #     # Call prompt template
    #     prompt, input_vars = load_prompt_template('ghostcoder.output')

    #     # Construct input message
    #     message = [
    #         SystemMessage(content=prompt.format()),
    #         HumanMessage(content=human_input)
    #     ]

    #     # Generate task instruction with llm
    #     i = 0
    #     while i < max_retry:
    #         try:
    #             respons = chat_model.invoke(message)
    #             break
    #         except Exception as e:
    #             i+=1
    #             if i == max_retry:
    #                 print(f"Error generating output: {e}")
    #                 raise  
        
    #     # Encapsulated execution code
    #     save_code_blocks(generated_codeblock)

    #     return {
    #         "task_result":  respons.content,
    #     }
    

    #----------------
    # Define conditional edges
    #----------------
    
    def router_use_RAG(state:State):
        if ghostcoder_config.DB_RETRIEVE:
            return "RAG"
        else:
            return "continue"
        
    def router_eval(state:State):
        if state['n_iter'] < ghostcoder_config.MAX_ITER:
            if state['eval_decision'].lower() == 'refine instruction':
                return "regen_instruc"
            elif state['eval_decision'].lower() == 'regenerate code':
                return "coder"
            else:
                return "output"
        else:
            return "output"
        
    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("File manager", node_filemanager)
    builder.add_node("Task parser", node_task_parser)
    builder.add_node("Retriever", node_retriever)
    builder.add_node("Coder",node_task_coder)
    builder.add_node("Evaluator",node_evaluator)
    builder.add_node("Output parser",node_output_parser)
    # builder.add_node("Update env",node_update_env)
    # add edges
    builder.add_edge(START, "File manager")
    builder.add_edge("File manager", "Task parser")
    builder.add_conditional_edges(
        "Task parser", 
        router_use_RAG,
        {
            "RAG"       : "Retriever", 
            "continue"  : "Coder"
        }
    )
    builder.add_edge("Retriever","Coder")
    builder.add_edge("Coder", "Evaluator")
    builder.add_conditional_edges(
        "Evaluator", 
        router_eval,
        {
            "regen_instruc" : "Task parser", 
            "coder"         : "Coder",
            "output"        : "Output parser",
        }
    )
    builder.add_edge("Output parser", END)


    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )