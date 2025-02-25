from __future__ import annotations

from sqlglot import exp, generator, parser, tokens
from sqlglot.dialects.dialect import (
    Dialect,
    arrow_json_extract_scalar_sql,
    arrow_json_extract_sql,
    format_time_lambda,
    no_paren_current_date_sql,
    no_tablesample_sql,
    no_trycast_sql,
    str_position_sql,
    trim_sql,
)
from sqlglot.helper import seq_get
from sqlglot.tokens import TokenType
from sqlglot.transforms import delegate, preprocess

DATE_DIFF_FACTOR = {
    "MICROSECOND": " * 1000000",
    "MILLISECOND": " * 1000",
    "SECOND": "",
    "MINUTE": " / 60",
    "HOUR": " / 3600",
    "DAY": " / 86400",
}


def _date_add_sql(kind):
    def func(self, expression):
        from sqlglot.optimizer.simplify import simplify

        this = self.sql(expression, "this")
        unit = self.sql(expression, "unit")
        expression = simplify(expression.args["expression"])

        if not isinstance(expression, exp.Literal):
            self.unsupported("Cannot add non literal")

        expression = expression.copy()
        expression.args["is_string"] = True
        expression = self.sql(expression)
        return f"{this} {kind} INTERVAL {expression} {unit}"

    return func


def _date_diff_sql(self, expression):
    unit = expression.text("unit").upper()
    factor = DATE_DIFF_FACTOR.get(unit)

    end = f"CAST({expression.this} AS TIMESTAMP)"
    start = f"CAST({expression.expression} AS TIMESTAMP)"

    if factor is not None:
        return f"CAST(EXTRACT(epoch FROM {end} - {start}){factor} AS BIGINT)"

    age = f"AGE({end}, {start})"

    if unit == "WEEK":
        extract = f"EXTRACT(year FROM {age}) * 48 + EXTRACT(month FROM {age}) * 4 + EXTRACT(day FROM {age}) / 7"
    elif unit == "MONTH":
        extract = f"EXTRACT(year FROM {age}) * 12 + EXTRACT(month FROM {age})"
    elif unit == "QUARTER":
        extract = f"EXTRACT(year FROM {age}) * 4 + EXTRACT(month FROM {age}) / 3"
    elif unit == "YEAR":
        extract = f"EXTRACT(year FROM {age})"
    else:
        self.unsupported(f"Unsupported DATEDIFF unit {unit}")

    return f"CAST({extract} AS BIGINT)"


def _substring_sql(self, expression):
    this = self.sql(expression, "this")
    start = self.sql(expression, "start")
    length = self.sql(expression, "length")

    from_part = f" FROM {start}" if start else ""
    for_part = f" FOR {length}" if length else ""

    return f"SUBSTRING({this}{from_part}{for_part})"


def _string_agg_sql(self, expression):
    expression = expression.copy()
    separator = expression.args.get("separator") or exp.Literal.string(",")

    order = ""
    this = expression.this
    if isinstance(this, exp.Order):
        if this.this:
            this = this.this
            this.pop()
        order = self.sql(expression.this)  # Order has a leading space

    return f"STRING_AGG({self.format_args(this, separator)}{order})"


def _datatype_sql(self, expression):
    if expression.this == exp.DataType.Type.ARRAY:
        return f"{self.expressions(expression, flat=True)}[]"
    return self.datatype_sql(expression)


def _auto_increment_to_serial(expression):
    auto = expression.find(exp.AutoIncrementColumnConstraint)

    if auto:
        expression = expression.copy()
        expression.args["constraints"].remove(auto.parent)
        kind = expression.args["kind"]

        if kind.this == exp.DataType.Type.INT:
            kind.replace(exp.DataType(this=exp.DataType.Type.SERIAL))
        elif kind.this == exp.DataType.Type.SMALLINT:
            kind.replace(exp.DataType(this=exp.DataType.Type.SMALLSERIAL))
        elif kind.this == exp.DataType.Type.BIGINT:
            kind.replace(exp.DataType(this=exp.DataType.Type.BIGSERIAL))

    return expression


def _serial_to_generated(expression):
    kind = expression.args["kind"]

    if kind.this == exp.DataType.Type.SERIAL:
        data_type = exp.DataType(this=exp.DataType.Type.INT)
    elif kind.this == exp.DataType.Type.SMALLSERIAL:
        data_type = exp.DataType(this=exp.DataType.Type.SMALLINT)
    elif kind.this == exp.DataType.Type.BIGSERIAL:
        data_type = exp.DataType(this=exp.DataType.Type.BIGINT)
    else:
        data_type = None

    if data_type:
        expression = expression.copy()
        expression.args["kind"].replace(data_type)
        constraints = expression.args["constraints"]
        generated = exp.ColumnConstraint(kind=exp.GeneratedAsIdentityColumnConstraint(this=False))
        notnull = exp.ColumnConstraint(kind=exp.NotNullColumnConstraint())
        if notnull not in constraints:
            constraints.insert(0, notnull)
        if generated not in constraints:
            constraints.insert(0, generated)

    return expression


def _to_timestamp(args):
    # TO_TIMESTAMP accepts either a single double argument or (text, text)
    if len(args) == 1:
        # https://www.postgresql.org/docs/current/functions-datetime.html#FUNCTIONS-DATETIME-TABLE
        return exp.UnixToTime.from_arg_list(args)
    # https://www.postgresql.org/docs/current/functions-formatting.html
    return format_time_lambda(exp.StrToTime, "postgres")(args)


class Postgres(Dialect):
    null_ordering = "nulls_are_large"
    time_format = "'YYYY-MM-DD HH24:MI:SS'"
    time_mapping = {
        "AM": "%p",
        "PM": "%p",
        "D": "%u",  # 1-based day of week
        "DD": "%d",  # day of month
        "DDD": "%j",  # zero padded day of year
        "FMDD": "%-d",  # - is no leading zero for Python; same for FM in postgres
        "FMDDD": "%-j",  # day of year
        "FMHH12": "%-I",  # 9
        "FMHH24": "%-H",  # 9
        "FMMI": "%-M",  # Minute
        "FMMM": "%-m",  # 1
        "FMSS": "%-S",  # Second
        "HH12": "%I",  # 09
        "HH24": "%H",  # 09
        "MI": "%M",  # zero padded minute
        "MM": "%m",  # 01
        "OF": "%z",  # utc offset
        "SS": "%S",  # zero padded second
        "TMDay": "%A",  # TM is locale dependent
        "TMDy": "%a",
        "TMMon": "%b",  # Sep
        "TMMonth": "%B",  # September
        "TZ": "%Z",  # uppercase timezone name
        "US": "%f",  # zero padded microsecond
        "WW": "%U",  # 1-based week of year
        "YY": "%y",  # 15
        "YYYY": "%Y",  # 2015
    }

    class Tokenizer(tokens.Tokenizer):
        BIT_STRINGS = [("b'", "'"), ("B'", "'")]
        HEX_STRINGS = [("x'", "'"), ("X'", "'")]
        BYTE_STRINGS = [("e'", "'"), ("E'", "'")]

        CREATABLES = (
            "AGGREGATE",
            "CAST",
            "CONVERSION",
            "COLLATION",
            "DEFAULT CONVERSION",
            "CONSTRAINT",
            "DOMAIN",
            "EXTENSION",
            "FOREIGN",
            "FUNCTION",
            "OPERATOR",
            "POLICY",
            "ROLE",
            "RULE",
            "SEQUENCE",
            "TEXT",
            "TRIGGER",
            "TYPE",
            "UNLOGGED",
            "USER",
        )

        KEYWORDS = {
            **tokens.Tokenizer.KEYWORDS,
            "~~": TokenType.LIKE,
            "~~*": TokenType.ILIKE,
            "~*": TokenType.IRLIKE,
            "~": TokenType.RLIKE,
            "BEGIN": TokenType.COMMAND,
            "BEGIN TRANSACTION": TokenType.BEGIN,
            "BIGSERIAL": TokenType.BIGSERIAL,
            "CHARACTER VARYING": TokenType.VARCHAR,
            "COMMENT ON": TokenType.COMMAND,
            "DECLARE": TokenType.COMMAND,
            "DO": TokenType.COMMAND,
            "GRANT": TokenType.COMMAND,
            "HSTORE": TokenType.HSTORE,
            "JSONB": TokenType.JSONB,
            "REFRESH": TokenType.COMMAND,
            "REINDEX": TokenType.COMMAND,
            "RESET": TokenType.COMMAND,
            "REVOKE": TokenType.COMMAND,
            "SERIAL": TokenType.SERIAL,
            "SMALLSERIAL": TokenType.SMALLSERIAL,
            "TEMP": TokenType.TEMPORARY,
            "UUID": TokenType.UUID,
            "CSTRING": TokenType.PSEUDO_TYPE,
            **{f"CREATE {kind}": TokenType.COMMAND for kind in CREATABLES},
            **{f"DROP {kind}": TokenType.COMMAND for kind in CREATABLES},
        }
        QUOTES = ["'", "$$"]
        SINGLE_TOKENS = {
            **tokens.Tokenizer.SINGLE_TOKENS,
            "$": TokenType.PARAMETER,
        }

    class Parser(parser.Parser):
        STRICT_CAST = False

        FUNCTIONS = {
            **parser.Parser.FUNCTIONS,  # type: ignore
            "TO_TIMESTAMP": _to_timestamp,
            "TO_CHAR": format_time_lambda(exp.TimeToStr, "postgres"),
        }

    class Generator(generator.Generator):
        TYPE_MAPPING = {
            **generator.Generator.TYPE_MAPPING,  # type: ignore
            exp.DataType.Type.TINYINT: "SMALLINT",
            exp.DataType.Type.FLOAT: "REAL",
            exp.DataType.Type.DOUBLE: "DOUBLE PRECISION",
            exp.DataType.Type.BINARY: "BYTEA",
            exp.DataType.Type.VARBINARY: "BYTEA",
            exp.DataType.Type.DATETIME: "TIMESTAMP",
        }

        TRANSFORMS = {
            **generator.Generator.TRANSFORMS,  # type: ignore
            exp.ColumnDef: preprocess(
                [
                    _auto_increment_to_serial,
                    _serial_to_generated,
                ],
                delegate("columndef_sql"),
            ),
            exp.JSONExtract: arrow_json_extract_sql,
            exp.JSONExtractScalar: arrow_json_extract_scalar_sql,
            exp.JSONBExtract: lambda self, e: self.binary(e, "#>"),
            exp.JSONBExtractScalar: lambda self, e: self.binary(e, "#>>"),
            exp.JSONBContains: lambda self, e: self.binary(e, "?"),
            exp.CurrentDate: no_paren_current_date_sql,
            exp.CurrentTimestamp: lambda *_: "CURRENT_TIMESTAMP",
            exp.DateAdd: _date_add_sql("+"),
            exp.DateSub: _date_add_sql("-"),
            exp.DateDiff: _date_diff_sql,
            exp.RegexpLike: lambda self, e: self.binary(e, "~"),
            exp.RegexpILike: lambda self, e: self.binary(e, "~*"),
            exp.StrPosition: str_position_sql,
            exp.StrToTime: lambda self, e: f"TO_TIMESTAMP({self.sql(e, 'this')}, {self.format_time(e)})",
            exp.Substring: _substring_sql,
            exp.TimeStrToTime: lambda self, e: f"CAST({self.sql(e, 'this')} AS TIMESTAMP)",
            exp.TimeToStr: lambda self, e: f"TO_CHAR({self.sql(e, 'this')}, {self.format_time(e)})",
            exp.TableSample: no_tablesample_sql,
            exp.Trim: trim_sql,
            exp.TryCast: no_trycast_sql,
            exp.UnixToTime: lambda self, e: f"TO_TIMESTAMP({self.sql(e, 'this')})",
            exp.DataType: _datatype_sql,
            exp.GroupConcat: _string_agg_sql,
            exp.Array: lambda self, e: f"{self.normalize_func('ARRAY')}({self.sql(e.expressions[0])})"
            if isinstance(seq_get(e.expressions, 0), exp.Select)
            else f"{self.normalize_func('ARRAY')}[{self.expressions(e, flat=True)}]",
        }
