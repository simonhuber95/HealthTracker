# img_viewer.py

import PySimpleGUI as sg
import os.path
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pathlib import Path
import traceback

matplotlib.use("TkAgg")

# Reading the Nutrition data
base_path = Path("./files")
food_data_path = (
    base_path / "MyFoodData.xlsx"
)  # "MyFoodData.xlsx"  # "testMyFoodData.xlsx"
my_meals_path = base_path / "MyMeals.xlsx"  # "MyMeals.xlsx"
macros_list = ["Fat (g)", "Protein (g)", "Carbohydrate (g)", "Sugars (g)", "Fiber (g)"]


class HealthTracker:
    def __init__(self, food_data_path, my_meals_path, macros_list):
        self.food_data_df = pd.read_excel(food_data_path, header=3, index_col=0)
        self.my_meals_path = my_meals_path
        self.my_meals_df = pd.read_excel(my_meals_path, header=0, index_col=0)
        self.macros_list = macros_list
        self.best_food_list = self.get_food_ranking()
        self.trusted_only = False
        self.layout = self.get_layout()
        self.window = sg.Window(
            "Health Tracker", self.layout, finalize=True, location=(0, 0)
        )
        # add the plot to the window
        self.fig = self.get_figure()
        self.fig_canvas_agg = self.draw_fig_agg(self.fig)
        self.run()

    def update_fig_agg(self):
        fig = self.get_figure(macros=self.macros_list, trusted_only=self.trusted_only)
        self.delete_fig_agg(self.fig_canvas_agg)
        fig_canvas_agg = self.draw_fig_agg(fig)
        return fig_canvas_agg

    def delete_fig_agg(self, fig_agg):
        fig_agg.get_tk_widget().forget()
        plt.close("all")

    def draw_fig_agg(self, figure):
        figure_canvas_agg = FigureCanvasTkAgg(figure, self.window["-CANVAS-"].TKCanvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side="top", fill="both", expand=1)
        return figure_canvas_agg

    def get_figure(self, macros=[], trusted_only=False):
        # plt.ioff()

        joined_df = pd.concat(
            [self.food_data_df, self.my_meals_df], axis=1, join="inner"
        )
        joined_df.fillna(0)
        # Filter df for trusted values
        if trusted_only:
            joined_df = joined_df[joined_df["Trust"]]
        plt.figure(figsize=(5, 5))
        fig = plt.gcf()
        axs1 = fig.add_subplot(211)
        axs2 = fig.add_subplot(212)
        # Summing the df on the Macros for pie chart
        sum_macros_df = joined_df[self.macros_list].T.sum(axis=1)
        sum_macros_df.plot.pie(ax=axs1, subplots=True)
        # Making corr matrix between rating and the macros
        if not joined_df.empty:
            corr_macros_df = (
                joined_df[self.macros_list + ["Rating"]]
                .corr()[["Rating"]][:-1]
                .sort_values(by="Rating", ascending=False)
            )
            print(corr_macros_df)
            heatmap = sns.heatmap(
                corr_macros_df, vmin=-1, vmax=1, annot=True, cmap="BrBG"
            )

        return fig

    def get_food_ranking(self, ascending=False, trusted_only=False):
        my_meals = self.my_meals_df
        if trusted_only:
            my_meals = my_meals[my_meals["Trust"]]
        ranked_df = my_meals.groupby("ID", as_index=True, sort=False).agg(
            {"Meallist": "first", "Rating": "mean"}
        )
        ranked_list = ranked_df.sort_values(
            by="Rating", axis=0, ascending=ascending
        ).values.tolist()
        return ranked_list

    def get_layout(self):
        # First the window layout in 2 columns
        meals_tab = [
            [
                sg.Text("Date", size=(5, 1), justification="left"),
                sg.InputText(key="-Date-"),
                sg.CalendarButton(
                    "Select Date",
                    close_when_date_chosen=True,
                    target="-Date-",
                    format="%d.%m.%Y",
                    size=(10, 1),
                ),
            ],
            [
                sg.Text("Meal", size=(5, 1), justification="left"),
                sg.Combo(
                    ["Breakfeast", "Lunch", "Dinner", "Snack"],
                    default_value="Breakfeast",
                    key="-Meal-",
                ),
            ],
            [
                sg.Text("Food", size=(5, 1), justification="left"),
                sg.Input(size=(20, 1), enable_events=True, key="-INPUT-"),
                sg.Checkbox("Starts with", default=False, key="-STARTSWITH-"),
            ],
            [sg.Listbox(values=[], enable_events=True, size=(60, 10), key="-LIST-")],
            [
                sg.Listbox(
                    values=[], enable_events=True, size=(60, 15), key="-MEALLIST-"
                )
            ],
            [
                sg.Text("Bad"),
                sg.Slider(
                    range=(1, 5),
                    tick_interval=1,
                    default_value=3,
                    orientation="h",
                    disable_number_display=True,
                    key="-RATING-",
                ),
                sg.Text("Good"),
            ],
            [sg.Checkbox("Data is trustworthy", default=False, key="-TRUST-")],
            [sg.Submit("Submit")],
        ]

        # For now will only show the name of the file that was chosen
        analysis_tab = [
            [
                sg.Combo(
                    self.food_data_df.columns[3:-19].values.tolist(),
                    key="-MACROS-",
                    enable_events=True,
                ),
                sg.Checkbox(
                    "Trusted entries only",
                    default=False,
                    enable_events=True,
                    key="-TRUSTENTRY-",
                ),
                sg.Button("Update", key="-UPDATEFIG-"),
            ],
            [
                sg.Listbox(
                    values=self.macros_list,
                    enable_events=True,
                    size=(40, 5),
                    key="-MACROSLIST-",
                ),
                sg.Table(
                    values=self.best_food_list,
                    headings=["Food", "Rating"],
                    enable_events=True,
                    size=(40, 5),
                    key="-BESTFOOD-",
                ),
            ],
            [sg.Sizer(h_pixels=600, v_pixels=0)],
            [
                sg.Canvas(
                    size=(800, 600),
                    pad=(5, 5, 5, 5),
                    expand_y=True,
                    expand_x=True,
                    # graph_bottom_left=(-105, -105),
                    # graph_top_right=(105, 105),
                    background_color="#FCF2EA",
                    key="-CANVAS-",
                )
            ],
        ]

        # ----- Full layout -----
        layout = [
            [
                [
                    sg.TabGroup(
                        [[sg.Tab("Meals", meals_tab), sg.Tab("Analysis", analysis_tab)]]
                    )
                ],
            ]
        ]
        return layout

    def run(self):

        # Run the Event Loop
        while True:
            event, values = self.window.read()
            if event == "Exit" or event == sg.WIN_CLOSED:
                break

            # Check for keystroke in Searchbar
            if values["-INPUT-"] != "":
                search = values["-INPUT-"]
                if values["-STARTSWITH-"]:
                    new_values = self.food_data_df.loc[
                        self.food_data_df["name"].str.startswith(search.capitalize())
                    ]["name"].to_list()
                else:
                    new_values = self.food_data_df.loc[
                        self.food_data_df["name"].str.contains(search, case=False)
                    ]["name"].to_list()
                new_values.sort()
                self.window["-LIST-"].update(new_values)  # display in the listbox
            # Add a Meal to Meallist
            if event == "-LIST-" and len(values["-LIST-"]):
                answer = sg.popup_yes_no(
                    "Do you want to add food to your meal? ", values["-LIST-"][0]
                )
                if answer == "Yes":
                    self.window["-MEALLIST-"].update(
                        self.window["-MEALLIST-"].get_list_values() + values["-LIST-"]
                    )
            # Delete Meal from Meallist
            if event == "-MEALLIST-" and len(values["-MEALLIST-"]):
                answer = sg.popup_yes_no(
                    "Do you want to delete food from your meal? ",
                    values["-MEALLIST-"][0],
                )
                if answer == "Yes":
                    self.window["-MEALLIST-"].get_list_values().pop(
                        self.window["-MEALLIST-"].get_indexes()[0]
                    )
                    self.window["-MEALLIST-"].update(
                        self.window["-MEALLIST-"].get_list_values()
                    )
            # Meal submit case
            if event == "Submit":
                print("save meal now")
                data = {
                    "ID": self.food_data_df[
                        self.food_data_df.name.isin(
                            self.window["-MEALLIST-"].get_list_values()
                        )
                    ].index.to_list(),
                    "Date": self.window["-Date-"].get(),
                    "Meal": self.window["-Meal-"].get(),
                    "Rating": values["-RATING-"],
                    "Trust": values["-TRUST-"],
                    "Meallist": self.window["-MEALLIST-"].get_list_values(),
                }
                df = pd.DataFrame.from_dict(data)

                with pd.ExcelWriter(
                    my_meals_path,
                    mode="a",
                    if_sheet_exists="overlay",
                    engine="openpyxl",
                ) as writer:
                    df.to_excel(
                        writer,
                        sheet_name="MyMeals",
                        startrow=writer.sheets["MyMeals"].max_row,
                        header=False,
                        index=False,
                    )
                self.window["-MEALLIST-"].update([])
                sg.popup("Meal was added to your list")

            # Update Analysis Tab
            if event == "-UpdateFig-":
                self.my_meals_df = pd.read_excel(my_meals_path, header=0, index_col=0)
                self.fig_canvas_agg = self.update_fig_agg()

            if event == "-MACROS-":
                macro = self.window["-MACROS-"].get()
                if macro not in self.macros_list:
                    self.macros_list.append(macro)
                    self.window["-MACROSLIST-"].update(self.macros_list)
                    self.fig_canvas_agg = self.update_fig_agg()

            if event == "-MACROSLIST-" and len(values["-MACROSLIST-"]):
                self.window["-MACROSLIST-"].get_list_values().pop(
                    self.window["-MACROSLIST-"].get_indexes()[0]
                )
                self.macros_list = self.window["-MACROSLIST-"].get_list_values()
                self.window["-MACROSLIST-"].update(self.macros_list)
                self.fig_canvas_agg = self.update_fig_agg()

            if event == "-TRUSTENTRY-":
                self.trusted_only = self.window["-TRUSTENTRY-"].get()
                self.fig_canvas_agg = self.update_fig_agg()
                self.best_food_list = self.get_food_ranking()
                self.window["-BESTFOOD-"].update(self.best_food_list)
        self.window.close()


try:
    healthtracker = HealthTracker(food_data_path, my_meals_path, macros_list)
except Exception as e:
    with open("log.txt", "a") as f:
        print(str(e))
        print(traceback.format_exc())
        f.write(str(e))
        f.write(traceback.format_exc())
