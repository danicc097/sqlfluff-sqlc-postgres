import logging
from colorama.ansi import Fore
import regex
from typing import Dict, Optional, Tuple


from sqlfluff.core.errors import SQLTemplaterError

from sqlfluff.core.templaters.base import (
    RawFileSlice,
    TemplatedFile,
    TemplatedFileSlice,
)

from sqlfluff.core.templaters.base import RawTemplater
import colorama
# Instantiate the templater logger
templater_logger = logging.getLogger("sqlfluff.templater")
logger = logging.Logger("sqlfluff_sqlc_postgres")
KNOWN_STYLES = {
    "sqlc": regex.compile(r"@(?P<param_name>[\w_]+)(::(?P<param_type>[\w_\[\]]+))?", regex.UNICODE),
}

AUTOFILL_PARAMS = {
    "integer_array": "ARRAY[1,2,3]",
    "text_array": "ARRAY['abc','def','ghi']",
    "boolean_array": "ARRAY[true,false,true]",
    "float_array": "ARRAY[1.1,2.2,3.3]",
    "string": "'string'",
    "integer": "1000",
    "float": "1.2345",
    "boolean": "true",
    "date": "CURRENT_DATE",
}


class SqlcPlaceholderTemplater(RawTemplater):
    """
    Based on the placeholder template.
    
    # See https://github.com/sqlfluff/sqlfluff/pull/2107
    
    """

    name = "sqlfluff-sqlc-postgres"

    def __init__(self, override_context=None, **kwargs):
        self.default_context = dict(test_value="__test__")
        self.override_context = override_context or {}

    # copy of the Python templater
    def get_context(self, config) -> Dict:
        """Get the templating context from the config."""
        # TODO: The config loading should be done outside the templater code. Here
        # is a silly place.
        if config:
            # This is now a nested section
            loaded_context = (
                config.get_section((self.templater_selector, self.name)) or {}
            )
        else:
            loaded_context = {}
        live_context = {}
        live_context.update(self.default_context)
        live_context.update(loaded_context)
        live_context.update(self.override_context)
        if "param_regex" in live_context and "param_style" in live_context:
            raise ValueError(
                "Either param_style or param_regex must be provided, not both"
            )
        if "param_regex" in live_context:
            live_context["__bind_param_regex"] = regex.compile(
                live_context["param_regex"]
            )
        elif "param_style" in live_context:
            param_style = live_context["param_style"]
            if param_style not in KNOWN_STYLES:
                raise ValueError(
                    'Unknown param_style "{}", available are: {}'.format(
                        param_style, list(KNOWN_STYLES.keys())
                    )
                )
            live_context["__bind_param_regex"] = KNOWN_STYLES[param_style]
        else:
            raise ValueError(
                "No param_regex nor param_style was provided to the placeholder templater!"
            )
        return live_context

    def _get_autofill_value(self, param_name: str, found_param, context=dict()) -> Optional[str]:
        """Get the autofill value for a parameter.

        Args:
            param_name: The name of the parameter.
            found_param: The found parameter.

        Returns:
            The autofill value for the parameter.

        """
        # SQL not typed
        if not found_param.groupdict().get("param_type"):
            templater_logger.info(
                f"No type was specified for parameter {param_name}. Assuming text."
            )
            if context.get("log_param_replacements"):
                print(Fore.RED + 
                f"No type was specified for parameter {param_name}. Assuming text."
            )
            return AUTOFILL_PARAMS["string"]

        param_type = found_param.groupdict()["param_type"].lower()
        if any(x in param_type for x in ["integer[]", "int[]"]):
            return AUTOFILL_PARAMS["integer_array"]
        elif "float[]" in param_type:
            return AUTOFILL_PARAMS["float_array"]
        elif "boolean[]" in param_type:
            return AUTOFILL_PARAMS["boolean_array"]
        elif "text[]" in param_type:
            return AUTOFILL_PARAMS["text_array"]
        elif any(x in param_type for x in ["integer", "int"]):
            return AUTOFILL_PARAMS["integer"]
        elif "float" in param_type:
            return AUTOFILL_PARAMS["float"]
        elif "boolean" in param_type:
            return AUTOFILL_PARAMS["boolean"]
        elif "date" in param_type:
            return AUTOFILL_PARAMS["date"]

        templater_logger.info(
            f"""Parsed type of parameter {param_name} was not recognized. Assuming text.
            You can manually specify the parameter value in your config file instead.
            """
        )
        if context.get("log_param_replacements"):
            print(Fore.RED + 
            f"""Parsed type of parameter {param_name} was not recognized. Assuming text.
            You can manually specify the parameter value in your config file instead.
            """
        )
        return AUTOFILL_PARAMS["string"]

    def process(
        self, *, in_str: str, fname: str, config=None, formatter=None
    ) -> Tuple[Optional[TemplatedFile], list]:
        """Process a string and return a TemplatedFile.

        Note that the arguments are enforced as keywords
        because Templaters can have differences in their
        `process` method signature.
        A Templater that only supports reading from a file
        would need the following signature:
            process(*, fname, in_str=None, config=None)
        (arguments are swapped)

        Args:
            in_str (:obj:`str`): The input string.
            fname (:obj:`str`, optional): The filename of this string. This is
                mostly for loading config files at runtime.
            config (:obj:`FluffConfig`): A specific config to use for this
                templating operation. Only necessary for some templaters.
            formatter (:obj:`CallbackFormatter`): Optional object for output.

        """
        context = self.get_context(config)
        template_slices = []
        raw_slices = []
        last_pos_raw, last_pos_templated = 0, 0
        out_str = ""

        regex = context["__bind_param_regex"]
        # when the param has no name, use a 1-based index
        param_counter = 1
        for found_param in regex.finditer(in_str):
            span = found_param.span()
            if "param_name" not in found_param.groupdict():
                param_name = str(param_counter)
                param_counter += 1
            else:
                param_name = found_param["param_name"]
            last_literal_length = span[0] - last_pos_raw

            if (
                context.get("autofill_missing_params")
                and param_name not in context.keys()
            ):
                replacement = self._get_autofill_value(param_name, found_param, context=context)
                if context.get("log_param_replacements"):
                    print(Fore.GREEN + f"Replacing {found_param.group(0)} with:", Fore.YELLOW + replacement)
            else:
                try:
                    replacement = context[param_name]
                    if context.get("log_param_replacements"):
                        print(Fore.GREEN + f"Replacing {found_param.group(0)} with:", Fore.YELLOW + replacement)
                except KeyError as err:
                    # TODO: Add a url here so people can get more help.
                    raise SQLTemplaterError(
                        "Failure in placeholder templating: {}. Have you configured your variables?".format(
                            err
                        )
                    )
            # add the literal to the slices
            template_slices.append(
                TemplatedFileSlice(
                    slice_type="literal",
                    source_slice=slice(last_pos_raw, span[0], None),
                    templated_slice=slice(
                        last_pos_templated,
                        last_pos_templated + last_literal_length,
                        None,
                    ),
                )
            )
            raw_slices.append(
                RawFileSlice(
                    raw=in_str[last_pos_raw : span[0]],
                    slice_type="literal",
                    source_idx=last_pos_raw,
                )
            )
            out_str += in_str[last_pos_raw : span[0]]
            # add the current replaced element
            start_template_pos = last_pos_templated + last_literal_length
            template_slices.append(
                TemplatedFileSlice(
                    slice_type="templated",
                    source_slice=slice(span[0], span[1], None),
                    templated_slice=slice(
                        start_template_pos, start_template_pos + len(replacement), None
                    ),
                )
            )
            raw_slices.append(
                RawFileSlice(
                    raw=in_str[span[0] : span[1]],
                    slice_type="templated",
                    source_idx=span[0],
                )
            )
            out_str += replacement
            # update the indexes
            last_pos_raw = span[1]
            last_pos_templated = start_template_pos + len(replacement)
        # add the last literal, if any
        if len(in_str) > last_pos_raw:
            template_slices.append(
                TemplatedFileSlice(
                    slice_type="literal",
                    source_slice=slice(last_pos_raw, len(in_str), None),
                    templated_slice=slice(
                        last_pos_templated,
                        last_pos_templated + (len(in_str) - last_pos_raw),
                        None,
                    ),
                )
            )
            raw_slices.append(
                RawFileSlice(
                    raw=in_str[last_pos_raw:],
                    slice_type="literal",
                    source_idx=last_pos_raw,
                )
            )
            out_str += in_str[last_pos_raw:]
        return (
            TemplatedFile(
                # original string
                source_str=in_str,
                # string after all replacements
                templated_str=out_str,
                # filename
                fname=fname,
                # list of TemplatedFileSlice
                sliced_file=template_slices,
                # list of RawFileSlice, same size
                raw_sliced=raw_slices,
            ),
            [],  # violations, always empty
        )
