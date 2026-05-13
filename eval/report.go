package main

import (
	"fmt"
	"os"
	"strings"
	"text/tabwriter"
)

const (
	colorReset  = "\033[0m"
	colorRed    = "\033[31m"
	colorGreen  = "\033[32m"
	colorYellow = "\033[33m"
	colorDim    = "\033[2m"
	colorBold   = "\033[1m"
)

func green(s string) string  { return colorGreen + s + colorReset }
func red(s string) string    { return colorRed + s + colorReset }
func yellow(s string) string { return colorYellow + s + colorReset }
func dim(s string) string    { return colorDim + s + colorReset }
func bold(s string) string   { return colorBold + s + colorReset }

func printSummary(results []FixtureResult) {
	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, bold("ID\tCATEGORY\tSTATUS\tELAPSED\tFAILURES"))
	fmt.Fprintln(w, strings.Repeat("─", 78))

	for _, fr := range results {
		status := green("PASS")
		if !fr.Passed {
			status = red("FAIL")
		}

		var failures []string
		if fr.Error != "" {
			failures = append(failures, red("exception: ")+truncate(fr.Error, 60))
		} else {
			for _, c := range fr.Checks {
				if !c.Passed {
					detail := ""
					if c.Detail != "" {
						detail = ": " + c.Detail
					}
					failures = append(failures, red(c.Name)+detail)
				}
			}
		}

		failStr := dim("—")
		if len(failures) > 0 {
			failStr = failures[0]
		}

		fmt.Fprintf(w, "%s\t%s\t%s\t%.2fs\t%s\n",
			fr.ID, fr.Category, status, fr.Elapsed.Seconds(), failStr,
		)
		for i, f := range failures {
			if i == 0 {
				continue
			}
			fmt.Fprintf(w, "\t\t\t\t%s\n", f)
		}
	}
	w.Flush()

	nPass := 0
	var totalElapsed float64
	for _, r := range results {
		if r.Passed {
			nPass++
		}
		totalElapsed += r.Elapsed.Seconds()
	}
	nTotal := len(results)

	fmt.Println()
	summary := fmt.Sprintf("%d/%d fixtures passed", nPass, nTotal)
	suffix := dim(fmt.Sprintf("(%.2fs total)", totalElapsed))
	if nPass == nTotal {
		fmt.Printf("%s  %s\n", green(bold(summary)), suffix)
	} else {
		fmt.Printf("%s  %s\n", red(bold(summary)), suffix)
	}
}
