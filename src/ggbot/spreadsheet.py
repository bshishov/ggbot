from typing import Optional, Dict, Tuple, Iterable
from dataclasses import dataclass

import gspread

from ggbot.assets import IndexedCollection
from ggbot.utils import local_time_cache


__all__ = ["SpreadsheetTable", "GoogleSpreadsheetsClient"]


def trim_sequence(sequence: Iterable) -> Iterable:
    result = []
    for item in sequence:
        if item:
            result.append(item)
        else:
            break
    return result


@dataclass
class SpreadsheetTable(IndexedCollection[dict]):
    worksheet: gspread.Worksheet
    header: Tuple[str, ...]
    key_field: Optional[str] = None
    first_row_index: int = 0

    @local_time_cache(5 * 60)
    def _get_data(self):
        values = self.worksheet.get_all_values()[self.first_row_index :]
        n_cols = len(self.header)

        if self.key_field is None:
            return {i: row[:n_cols] for i, row in enumerate(values)}

        key_col_ix = self.header.index(self.key_field)
        ix = {}
        for row in values:
            if row:
                ix[row[key_col_ix]] = row
        return ix

    def get_item_by_index(self, index):
        return self._get_data()[index]

    def iter_items(self) -> Iterable[dict]:
        yield from self._get_data().values()

    def __len__(self):
        return len(self._get_data())


def table_from_worksheet(
    worksheet: gspread.Worksheet, header: Optional[Tuple[str]] = None
):
    if header:
        return SpreadsheetTable(worksheet, header=header)

    header = tuple(trim_sequence(worksheet.row_values(1)))
    return SpreadsheetTable(worksheet, header, first_row_index=1)


@dataclass
class GoogleSpreadsheetsClient:
    client: gspread.Client

    def get_table_by_title(
        self, spreadsheet_name: str, worksheet: str
    ) -> IndexedCollection:
        sheet = self.client.open(spreadsheet_name).worksheet(worksheet)
        return table_from_worksheet(sheet)

    def get_table_by_key(
        self, spreadsheet_key: str, worksheet: str
    ) -> IndexedCollection:
        sheet = self.client.open_by_key(spreadsheet_key).worksheet(worksheet)
        return table_from_worksheet(sheet)

    @classmethod
    def from_file(cls, filename: str):
        return GoogleSpreadsheetsClient(gspread.service_account(filename))

    @classmethod
    def from_service_account_dict(cls, service_account: Dict):
        return GoogleSpreadsheetsClient(
            gspread.service_account_from_dict(service_account)
        )
