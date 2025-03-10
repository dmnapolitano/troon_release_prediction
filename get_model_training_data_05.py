from datetime import datetime, date
import warnings

import pandas
import numpy as np
import holidays
import statsmodels.api as sm
from statsmodels.othermod.betareg import BetaModel
from statsmodels.tools.sm_exceptions import HessianInversionWarning, ConvergenceWarning
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils.validation import check_is_fitted, check_array


def get_holidays(years):
    nj_holidays = holidays.UnitedStates(state="NJ", years=years)
    nj_holidays.append({"{}-03-17".format(y) : "St. Patrick's Day" for y in years})
    nj_holidays.append({"{}-02-14".format(y) : "Valentine's Day" for y in years})
    nj_holidays.append({"{}-12-24".format(y) : "Christmas Eve" for y in years})
    nj_holidays.append({"{}-12-31".format(y) : "New Year's Eve" for y in years})

    # Super Bowls count as holidays as far as beer is concerned lol
    nj_holidays["2016-02-07"] = "Super Bowl 50"
    nj_holidays["2017-02-05"] = "Super Bowl LI"
    nj_holidays["2018-02-04"] = "Super Bowl LII"
    nj_holidays["2019-02-03"] = "Super Bowl LIII"
    nj_holidays["2020-02-02"] = "Super Bowl LIV"
    nj_holidays["2021-02-07"] = "Super Bowl LV"
    nj_holidays["2022-02-13"] = "Super Bowl LVI"
    nj_holidays["2023-02-12"] = "Super Bowl LVII"
    nj_holidays["2024-02-11"] = "Super Bowl LVIII"
    nj_holidays["2025-02-09"] = "Super Bowl LIX"

    return nj_holidays


def get_features_and_data(data_csv="troon_instagram_clean_post_data.csv"):
    def _get_features(df, nj_holidays, count_df):
        # in addition to days_since_previous_release
        
        df["next_holiday"] = df["index"].apply(lambda x : min([h for h in nj_holidays if h >= x.date()]))
        df["days_until_next_holiday"] = pandas.to_timedelta(df["next_holiday"] - df["index"].dt.date).dt.days
        del df["next_holiday"]
        
        df["weekday"] = df["index"].apply(lambda x : x.strftime("%A"))
        if "year" not in df.columns:
            df["year"] = df["index"].dt.year
            
        df["copy"] = df["weekday"].copy()
        df = pandas.get_dummies(df, columns=["copy"], prefix="WD", drop_first=True, dtype=int)
    
        if "previous_release" not in df.columns:
            df["previous_release"] = df["release"].astype("Int64").shift().fillna(0).astype(int)

        if "previous_release_preorder" not in df.columns:
            df["previous_release_preorder"] = df["release_preorder"].shift().fillna(False).astype(int)

        df = df.merge(count_df, on=["year", "days_since_previous_release"], how="left")
        df["release_prob"] = df["release_prob"].fillna(0)
        
        return df
    
    
    df = pandas.read_csv(data_csv)
    df = df.set_index("id")
    df = df[df["days_since_previous_release"].notnull()].copy()
    df = df[["post_month", "post_day", "post_year", "days_since_previous_release", "release_post", "release_preorder"]].copy()
    df["month"] = df["post_month"].apply(lambda x : datetime.strptime(x, '%B').month)
    df = df.rename(columns={"post_year" : "year", "post_day" : "day", "release_post" : "release"})
    df["date"] = pandas.to_datetime(df[["year", "month", "day"]])
    df = df.drop(columns=["post_month", "day", "month"])
    df = df.drop_duplicates(subset=["date"])
    
    df = df[df["release"] == True].copy()
    df["release"] = df["release"].astype("Int64")

    nj_holidays = get_holidays(set(df["year"]))
    del df["year"]

    df = df.sort_values(by=["date"]).set_index("date")
    daily = pandas.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(daily, method=None)
    df["release"] = df["release"].fillna(0)
    df["release_preorder"] = df["release_preorder"].fillna(False)

    df = df.reset_index()
    release_dates = list(df[df["release"] == 1]["index"])
    df["closest_release_date"] = df["index"].apply(lambda x : max([d for d in release_dates if d <= x]))

    df["backfill"] = (df["index"] - df["closest_release_date"]).values.astype("timedelta64[D]").astype(float)
    df["days_since_previous_release"] = df["days_since_previous_release"].fillna(df["backfill"])
    del df["backfill"]
    del df["closest_release_date"]

    # probability target variable
    df["future_release_dates"] = df["index"].apply(lambda x : [d for d in release_dates if d > x])
    df["future_release_date"] = df["future_release_dates"].apply(lambda x : min(x) if len(x) > 0 else max(release_dates))
    del df["future_release_dates"]
    df["days_until_next_release"] = (df["future_release_date"] - df["index"]).values.astype("timedelta64[D]").astype(float)
    del df["future_release_date"]

    df["prob_of_release"] = (df["days_since_previous_release"] /
                             (df["days_since_previous_release"] + df["days_until_next_release"]))
    df = df[df["prob_of_release"].notnull()].copy()
    df["prob_of_release"] = df.apply(lambda x : 1 if x["release"] == 1 else x["prob_of_release"], axis=1)
    ###

    df["year"] = df["index"].dt.year
    count_df = df[df["release"] == 1].groupby(["year", "days_since_previous_release"]).size().reset_index()
    count_df = count_df.merge(df[df["release"] == 1].groupby(["year"]).size().reset_index().rename(columns={0 : "total"}),
                              on=["year"], how="left")
    count_df["release_prob"] = count_df[0] / count_df["total"]
    count_df = count_df.drop(columns=[0, "total"])

    df = _get_features(df.copy(), nj_holidays, count_df)
    df = df[df["year"] >= 2023].copy()

    train_df = df[df["index"] < "2024-12-01"].copy()
    test_df = df[~df.index.isin(train_df.index)].copy()
    print(f"training examples = {len(train_df)}, testing examples = {len(test_df)}")

    features = [c for c in df.columns if c not in ["index", "prob_of_release", "release", "month", "weekday", "year", "days_until_next_release", "release_preorder"]]

    last_release_date = test_df[test_df["release"] == 1][-1:].iloc[0]["index"]
    next_two_weeks = pandas.DataFrame([{"index" : t} for t in 
                                       pandas.date_range(start=date.today(), freq="1D", periods=14)])
    next_two_weeks["days_since_previous_release"] = (next_two_weeks["index"] - last_release_date).dt.days
    next_two_weeks["previous_release"] = next_two_weeks["days_since_previous_release"].apply(lambda x : 1 if x <= 1 else 0)
    next_two_weeks["previous_release_preorder"] = test_df[test_df["release"] == 1][-1:].iloc[0]["release_preorder"]
    next_two_weeks = _get_features(next_two_weeks, nj_holidays, count_df)
    
    for f in features:
        if f not in next_two_weeks.columns:
            next_two_weeks[f] = 0

    return (df, train_df, test_df, features, next_two_weeks)


def get_features_and_data_monthly(data_csv="troon_instagram_clean_post_data.csv", lags=1):
    # possible ideas for features:
    # average number of releases per weekday per month (lagged)
    # number of pre-orders in the previous month
    
    df = pandas.read_csv(data_csv)
    df = df.set_index("id")
    df = df[df["days_since_previous_release"].notnull()].copy()
    df = df[["post_month", "post_day", "post_year", "days_since_previous_release", "release_post", "release_preorder"]].copy()
    df["month"] = df["post_month"].apply(lambda x : datetime.strptime(x, '%B').month)
    df = df.rename(columns={"post_year" : "year", "post_day" : "day", "release_post" : "release"})
    df["date"] = pandas.to_datetime(df[["year", "month", "day"]])
    df = df.drop(columns=["post_month", "day", "month"])
    df = df.drop_duplicates(subset=["date"])
    
    df = df[df["release"] == True].copy()
    df["release"] = df["release"].astype("Int64")
    # df["release_preorder"] = df["release_preorder"].astype("Int64") # TODO

    nj_holidays = get_holidays(set(df["year"]))
    del df["year"]

    df = df.sort_values(by=["date"]).set_index("date")
    daily = pandas.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(daily, method=None)
    df = df.reset_index()
    df["month_year"] = df["index"].dt.to_period("M")

    df = df.groupby(["month_year"]).agg(
        {"days_since_previous_release" : "mean", "release" : "sum"}) #, "release_preorder" : "sum"}) # TODO
    df = df.reset_index()
    df = df.rename(columns={"days_since_previous_release" : "avg_days_since_previous_release", "release" : "n_releases"})

    current_month = pandas.to_datetime(date.today()).to_period("M")

    if not (df["month_year"] == current_month).any():
        df = pandas.concat([df, pandas.DataFrame([{"month_year" : current_month}])], ignore_index=True)
    
    df["month_holidays"] = df["month_year"].apply(
        lambda x : len([h for h in nj_holidays if h.month == x.month and h.year == x.year]))
    df["month_holidays"] = df["month_holidays"].astype(int)
    df["prior_avg_days_since_previous_release"] = df["avg_days_since_previous_release"].shift().fillna(0)

    features = ["prior_avg_days_since_previous_release", "month_holidays"]
    # target = "n_releases"

    if lags > 0:
        df["lag1"] = df["n_releases"].shift().fillna(0).astype(int)        
        features.append("lag1")
        for l in range(1, lags):
            df[f"lag{l + 1}"] = df[f"lag{l}"].shift().fillna(0).astype(int)
            features.append(f"lag{l + 1}")

    next_df = df[df["month_year"] == current_month].copy()
    test_df = df[df["month_year"] != current_month][-10:].copy()
    train_df = df[(~df.index.isin(test_df.index)) & (~df.index.isin(next_df.index))].copy()

    print(f"training examples = {len(train_df)}, testing examples = {len(test_df)}")

    return (df, train_df, test_df, features, next_df)


def weighted_absolute_percentage_error(Y_expected, Y_pred):
    if isinstance(Y_expected, list):
        Y_expected = np.array(Y_expected)
    if isinstance(Y_pred, list):
        Y_pred = np.array(Y_pred)

    absolute_errors = np.abs(Y_expected - Y_pred)
    error_sum = np.sum(absolute_errors)

    return error_sum / np.sum(Y_expected)


class BetaRegression(BaseEstimator, RegressorMixin):
    def __init__(self, fit_intercept=True):
        self.fit_intercept = fit_intercept


    def fit(self, X, y):
        X_temp, y = self._validate_data(
            X, y, accept_sparse=False, y_numeric=True, multi_output=True
        )
        X = pandas.DataFrame(X_temp, columns=X.columns, index=X.index)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=HessianInversionWarning)
            warnings.simplefilter("ignore", category=ConvergenceWarning)
            if self.fit_intercept:
                self.beta_ = BetaModel(y, sm.add_constant(X, has_constant="add"))
            else:
                self.beta_ = BetaModel(y, X)
            self.model_ = self.beta_.fit()

        coefs = self.model_.params.copy()
        if self.fit_intercept:
            self.intercept_ = coefs["const"]
            del coefs["const"]
        del coefs["precision"]
        self.feature_names_in_ = list(coefs.index)
        self.coef_ = coefs.values
        self.n_features_in_ = len(coefs)


    def predict(self, X):
        check_is_fitted(self, "model_")

        # Input validation
        X = check_array(X)
        
        if self.fit_intercept:
            X = sm.add_constant(X, has_constant="add")

        return self.model_.predict(X)


    def get_params(self, deep=False):
        return {"fit_intercept" : self.fit_intercept}


if __name__ == "__main__":
    # (df, train_df, test_df, features, next_month) = get_features_and_data()
    (df, train_df, test_df, features, next_month) = get_features_and_data_monthly()
    print(features)
    print()
    print(df)
    print()
    print(next_month)
