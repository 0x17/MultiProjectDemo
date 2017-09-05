import openpyxl
import json


def column_as_list(ws, column_name, start_row_index, end_row_index):
    return [cell.value for cell in ws[column_name][start_row_index - 1:end_row_index]]


def indicator_column_to_sublist(ws, column_name, start_row_index, end_row_index):
    return [row_ix - start_row_index + 1 for row_ix in range(start_row_index, end_row_index + 1) if
            ws[column_name][row_ix - 1].value == 'yes']


def rect_map(ws, f, top_left_indices, bottom_right_indices):
    tl_x, tl_y = top_left_indices
    br_x, br_y = bottom_right_indices
    return [[f(cell) for cell in row] for row in
            ws.iter_rows(min_row=tl_x, max_row=br_x, min_col=tl_y, max_col=br_y)]


def rect_as_list_of_rows(ws, top_left_indices, bottom_right_indices):
    return rect_map(ws, lambda cell: cell.value, top_left_indices, bottom_right_indices)


def rect_as_list_of_boolean_rows(ws, top_left_indices, bottom_right_indices):
    return rect_map(ws, lambda cell: cell.value == 'yes', top_left_indices, bottom_right_indices)


def write_as_json(dict, out_filename):
    with open(out_filename, 'w') as fp:
        fp.write(json.dumps(dict, sort_keys=True, indent=4))


def main():
    wb = openpyxl.load_workbook('Input.xlsx')

    for i in range(3):
        worksheet_name = 'Projekt ' + str(i + 1)
        ws = wb[worksheet_name]

        project = {
            'jobs': column_as_list(ws, 'A', 6, 15),
            'durations': column_as_list(ws, 'B', 6, 15),
            'demands': [column_as_list(ws, 'C', 6, 15)],
            'capacities': [wb['Globals']['C3'].value, wb['Globals']['F3'].value],
            'mandatory_activities': indicator_column_to_sublist(ws, 'E', 6, 15),
            'job_in_decision': rect_as_list_of_boolean_rows(ws, (6, 6), (15, 6)),
            'job_activating_decision': rect_as_list_of_boolean_rows(ws, (6, 7), (15, 7)),
            'job_causing_job': rect_as_list_of_boolean_rows(ws, (6, 8), (15, 17)),
            'precedence': rect_as_list_of_boolean_rows(ws, (6, 18), (15, 27)),
            'deadline': ws['B18'].value,
            'delaycost': ws['B19'].value
        }

        write_as_json(project, 'Projekt' + str(i + 1) + '.json')


if __name__ == '__main__': main()
