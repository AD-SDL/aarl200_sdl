from math import exp
from re import S
import sys, os, glob
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import periodictable                    # for ion ordering
import statsmodels.api as sm            # for permeation slope analysis
# model fits (MLR w optional quadratic expansion)
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_squared_error


class AMEWS_analysis:
    
    def __init__(self, exp = None):
        self.ref_mode = 2 # 1 - normalize each sample by standard in the sample
                          # 2 - in addition, normalize by the external standard
        self.std = "Y" # ICP calibration standard 
        self.fsum = "summary" 
        if self.ref_mode:
            self.fsum +="_ref%d" % self.ref_mode
        self.elall = []
        self.ext = None
        self.unit = "ppm"

        if exp:
            if os.path.isdir(exp):
                self.res = exp
            else:
                print(">> Results folder not found, abort")
                sys.exit(0)
        else:
            root = tk.Tk()
            self.res = filedialog.askdirectory(title="Select records folder")
            
        full = glob.glob(os.path.join(self.res, "*-*.csv"))
        partial  = [os.path.splitext(os.path.basename(f))[0] for f in full]
        self.names = sorted(partial, key=self.cell_index)
        print(">> Found records folder %s" % self.res)
        print(">> Found %d records: %s" % (len(self.names), self.names))

    def cell_index(self, name):
        try:
            return int(name.split('-')[-1])
        except:
            return 0
        
    def analyze_all_records(self):
        self.analyze_records(self.names)
        
    def analyze_one_record(self, name):
        self.analyze_records([name])

    def analyze_records(self, names):
        f= os.path.join(self.res, "%s.pdf" % self.fsum)
        self.pdf = PdfPages(f)
        self.summary = []
        
        for name in names:
            self.analyze_record(name, 1) # make a global list of elements
            
        self.elall = sorted(self.elall, key=lambda el: periodictable.elements.symbol(el).number)

        print("\n =============== All feed elements: %s ============== \n" % self.elall)

        for name in names:
            self.analyze_record(name)
            for elmnt in self.elmode:
                self.analyze_elmnt(elmnt)

        f= os.path.join(self.res, "%s.csv" % self.fsum)
        q = pd.DataFrame(self.summary)
        q.to_csv(f, index=False)
        self.axial_radial_corr_plot()
        self.pdf.close()

    def analyze_record(self, name, opt=0):
        self.name = name
        self.file = os.path.join(self.res, self.name + ".csv")
        self.cell = self.cell_index(self.name)
        s = "%s," % self.std
        self.elfeed = []
        print("\n>> Cell = %d, address = %s" % (self.cell, self.name))
        try: 
            self.record = pd.read_csv(self.file)

            for col in self.record.columns:
                if ',' in col and s not in col:
                    el = col.split(',')[0]
                    self.elfeed.append(el)
                    if el not in self.elall:
                        self.elall.append(el)
            print(">> Feed elements = %s" % self.elfeed)
            if opt: return 1

            self.unit = self.record.columns[-1].split(",")[1]
            print(">> Concentration unit = %s" % self.unit)
            self.feed = self.record["feed"].dropna().unique().astype(int).tolist()
            print(">> Feeds = %s" % self.feed)

            self.elmode = []
            for col in self.record.columns:
                if 'radial_' in col or 'axial_' in col:
                    el = col.split("_")[1]
                    if el in self.elfeed:
                        self.elmode.append(col)
            print(">> ICP analyses = %s" % self.elmode)
            
            # external standards
            self.ext = None
            mode = ["radial_","axial_"]
            df = self.record[self.record["kind"].str.contains("standard", case=False, na=False)]
            df = df.drop(columns=[col for col in df.columns if ',' in col])
            df = df.drop(columns=["th", "sample", "feed", "volume", "chaser"])

            if not df.empty:
                for m in mode:
                    s = m + self.std
                    if s in df.columns:
                        for col in df.columns: 
                            if m in col:
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                                df.loc[:, col] = df[col].div(df[s], axis=0)
                        df = df.drop(columns=[s])

            if not df.empty:
                self.ext = df.groupby("category", as_index=False).mean(numeric_only=True)
                f = os.path.join(self.res, "QC_ref_std.csv")
                df.to_csv(f, index=False)
                del(df)

            return 1

        except Exception as e:
            print(">>> Error = %s" % e)
            sys.exit(0)
            
        return 0

    def analyze_elmnt(self, elmnt):
        if elmnt not in self.elmode:
            return 0
        self.elmnt = elmnt
        for j in self.feed:
            print("+++ element = %s, feed %d" % (elmnt, j))
            df = self.record[self.record["feed"] == j]
            df = df[df["kind"] == "analyte"]
            x = df["th"].to_numpy().astype(float)
            y = df[elmnt].to_numpy().astype(float)
            tmax = np.max(x)
            
            if self.ref_mode: 
                s = self.reference_std()
                if s: 
                    scale = df[s].to_numpy().astype(float)
                    y /= scale

            if self.ref_mode==2:
                n=0 
                for i, _ in df.iterrows():
                    u = self.reference_std_ext(elmnt, i)
                    try: 
                        y[n] /= u
                    except:
                        y[n] = np.nan
                    n+=1
                    
            del(df)
            
            u = self.linear_fit(x, y)
            if u is not None:
                r = {"cell" : self.cell, "address" : self.name, "element" : elmnt}
                r.update(u)
                r["calibration"] = self.find_calibration()
                r["check"] = 100*tmax*r["slope"]/r["calibration"]
                r["feed"] = j
                for el in self.elall:
                    s= "%s,%s" % (el, self.unit)
                    r[s] = self.find_feed(s, j)
                self.summary.append(r)

    def reference_std_ext(self, elmnt, index):
        if self.ext is not None:
            category = self.record.loc[index, "category"]
            if elmnt in self.ext.columns:
                for _, r in self.ext.iterrows():
                    if r["category"] == category:
                        return r[elmnt]
        return np.nan
    
    def reference_std(self):
         if "radial" in self.elmnt:
             s = "radial_%s" % self.std
         else:
             s = "axial_%s" % self.std
         if s in self.record.columns:
             return s
         else: 
             return None

    def find_feed(self, s, j):
        if s in self.record.columns:
            for _, r in self.record.iterrows():
                if r["feed"]==j:
                    return r[s]
        return np.nan

    def find_calibration(self):
        s = self.reference_std()
        if self.ref_mode and s is None:
            return np.nan
        
        for i, r in self.record.iterrows():
            if r["kind"]=="calibration":
                x = r[self.elmnt]
                y = r[s]
                z = self.reference_std_ext(self.elmnt, i+1)
                if self.ref_mode:
                   try: 
                       x/=y
                       if self.ref_mode==2: x/=z
                       return x
                   except: 
                       return np.nan
                return x
        return np.nan

    def linear_fit(self, x, y):
        
            mask = ~np.isnan(x) & ~np.isnan(y)
            x1 = x[mask]
            y1 = y[mask]
            
            if len(y1)<3:
                return None
            
            X = sm.add_constant(x1)
    
            # Fit the model using OLS (Ordinary Least Squares)
            model = sm.OLS(y1, X)
            results = model.fit()
            rmse = np.sqrt(np.mean(results.resid**2))
            
            y1[np.abs(results.resid) > 2*rmse] = np.nan
            mask = ~np.isnan(y1)
            x2 = x1[mask]
            y2 = y1[mask]
            X = sm.add_constant(x2)
            model = sm.OLS(y2, X)
            results = model.fit()
            
            if len(y2)<3:
                return None

            param = {  "slope" : results.params[1],
                    "dslope, %" : 100.*results.bse[1]/results.params[1],
                    "R^2" : results.rsquared }
            
            x = np.linspace(0, np.max(x2)*1.1, 50)
            X = sm.add_constant(x)
            y = results.predict(X)
            
            fig = plt.figure(figsize=(6,4))
            plt.plot(x, y, color='blue', label='Linear fit')
            if "axial_" in self.elmnt:
                plt.plot(x2, y2, 'o', color = 'red', label='Data') 
            else:
                plt.plot(x2, y2, 'o', color='red', markeredgewidth=2, markerfacecolor='none', label='Data')
            plt.xlim(0, np.max(x2) * 1.1)  # Set X-axis from 0 to max(xc), even if negatives exist in original data
            plt.ylim(0, np.max(y2) * 1.1) 
            plt.xlabel("time, h")
            s = self.elmnt.replace("_", " ")
            if self.ref_mode: 
               s = "%s/%s" % (s, self.std)
               if self.ref_mode:
                   s += " w external corr."
            plt.ylabel(s)
            s = self.name.split("-")
            s = "cell %s, %s:%s" % (s[2], s[0], s[1])
            plt.title(s, fontweight='bold')
            plt.legend()
            plt.minorticks_on()
            plt.grid(True)
            
            self.pdf.savefig(fig)
            f = os.path.join(self.res, "%s_%s.jpg" % (self.name, self.elmnt))
            # plt.savefig(f, format='jpg', dpi=300)
            plt.close(fig)

            return param
    
    def find_mode_match(self, address, elmnt):
        i = 0
        for r in self.summary:
            if r["address"]==address and r["element"]==elmnt:
                return i
            i+=1
        return -1

    def axial_radial_corr_plot(self):
        if not self.summary:   return 0

        x=[] # radial slope
        y=[] # axial slope 
        c=[] # cell
        
        for r in self.summary:
            mode, el = r["element"].split("_")
            if mode=="radial":
                j = self.find_mode_match(r["address"], "axial_%s" % el)
                if j>=0:
                    x.append(r["slope"])
                    y.append(self.summary[j]["slope"])
                    c.append(r["cell"])

        fig = plt.figure(figsize=(4,4))
        plt.xlabel("radial slope")
        plt.ylabel("axial slope")
        plt.title("ICP correlation, ref. mode=%d" % self.ref_mode, fontweight='bold')
        scatter = plt.scatter(x, y, c=c, cmap='rainbow')
        bar = plt.colorbar(scatter, orientation='horizontal')
        bar.set_label("cell")
        
        if self.ref_mode==2:
            xymax = 1.1*max(max(x),max(y))
            plt.xlim(0, xymax)
            plt.ylim(0, xymax)
            z = np.linspace(0, xymax, 50)
            plt.plot(z, z, color='black', linestyle='--')
            
        plt.minorticks_on()
        plt.grid(True)
        plt.tight_layout()
        
        self.pdf.savefig(fig)
        f = os.path.join(self.res, "mode_corr_plot.jpg")
        plt.savefig(f, format='jpg', dpi=300)
        plt.close(fig)
                
        return 1
    
    def do_fit(self, mask):
        self.elmnt=mask
        xc=[]
        yc=[]
        for r in self.summary:
            if r["element"]==mask and not np.isnan(r["calibration"]):
                v = []
                for el in self.elall:
                    s= "%s,%s" % (el, self.unit)
                    if not np.isnan(r[s]):
                        v.append(r[s])
                    else: v.append(0)
                xc.append(v)
                yc.append(r["slope"]/r["calibration"])

        x=np.array(xc)
        y=np.array(yc)

        self.poly_fit(x,y)

    def return_pipeline(self, x, y, k_): # Quadratic MLR for k_ most important features

        poly = PolynomialFeatures(degree=2, include_bias=False)
        selector = SelectKBest(score_func=f_regression, k=k_)
        model = LinearRegression()
        pipeline = make_pipeline(poly, selector, model)
        pipeline.fit(x, y)
        yp = pipeline.predict(x)
        mse = mean_squared_error(y, yp) # rms
        rms = np.sqrt(mse)
        aic = x.shape[0] * np.log(rms) + 2*k_ # Akaike information criterion 
        return pipeline, rms, aic
    
    def choose_best_k(self, x, y, kmax):
        u = np.inf
        best_k = 1
        for k in range(1, kmax+1):
            _, _, aic = self.return_pipeline(x, y, k)
            if aic<u:
                u = aic
                best_k = k
        return best_k

    def poly_fit(self, x, y, kmax=5): # quadratic fitting with k most important features

        print("\n>> Quadratic MLR fit for %s" % self.elmnt)
        print(">> %d primary features: %s" % (len(self.elall), self.elall))
        print(">> Retains <= %d terms" % kmax)

        best_k = self.choose_best_k(x, y, kmax)
        print(">> %d important terms by AIC criterion" % best_k)

        pipeline, rms, _ = self.return_pipeline(x, y, best_k)
        yp = pipeline.predict(x)
        r2 = pipeline.score(x, y)
        poly_step = pipeline.named_steps['polynomialfeatures']
        selector_step = pipeline.named_steps['selectkbest']
        model_step = pipeline.named_steps['linearregression']

        # F-scores and feature selection
        f_scores = selector_step.scores_
        all_feature_names = poly_step.get_feature_names_out(input_features=self.elall)
        selected_indices = selector_step.get_support(indices=True)
        selected_feature_names = all_feature_names[selected_indices]
        selected_f_scores = [f_scores[i] for i in selected_indices]

        # Output
        print(">> Coefficients:", model_step.coef_)
        print(">> Intercept:", model_step.intercept_)
        print(">> Selected F-scores:", selected_f_scores)
        print(">> Selected features:", selected_feature_names)
        print(">> rms = %.2e, R^2 =%.3f" % (rms, r2))

        out = os.path.join(self.res,"fit_%s.csv" % self.elmnt)
        df = pd.DataFrame(x, columns=["%s,%s" % (el, self.unit) for el in self.elall])
        df["y"] = y
        df["y_fit"] = yp
        df["error %"] = 100*(1-yp/y)
        df.to_csv(out, index=False)

        with open(out, "a") as f:
            f.write("\n\nQuadratic MLR fit\n%d,selected features" % best_k)
            f.write("\nrms,%.3e\nR^2,%.3f" % (rms, r2))
            f.write("\nIntercept,%.3e" % model_step.intercept_)
            f.write("\nfeatures,F-score,coefficient")
            for name, score, c in zip(selected_feature_names, selected_f_scores,model_step.coef_):
                f.write("\n%s,%.3f,%.3e" % (name, score, c))
            f.close()

def main():
    x = AMEWS_analysis()
    #x.analyze_one_record(x.names[0])
    x.analyze_all_records()
    x.do_fit("radial_Li")

if __name__ == "__main__":
    main()


