// DumpFileTran.java - lists file_tran strings, their xrefs and containing functions; decompiles them.
// Headless: analyzeHeadless <proj> cubitt -process -noanalysis -scriptPath <dir> -postScript DumpFileTran.java
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.util.*;

public class DumpFileTran extends GhidraScript {
    String[] needles = {
        "protocol_file_tran", "file_tran_port_dfu", "get_offset",
        "prn:", "file_name", "tran_request", "file_tran",
        "queue_is_emety", "queue_is_empty", "port_dfu"
    };
    long[] known = { 0x100cfe94L };

    DecompInterface di;
    LinkedHashSet<Long> funcs = new LinkedHashSet<>();

    private String decomp(Function f) {
        DecompileResults r = di.decompileFunction(f, 90, monitor);
        if (r != null && r.decompileCompleted()) return r.getDecompiledFunction().getC();
        return "(decompile failed)";
    }

    @Override
    public void run() throws Exception {
        di = new DecompInterface();
        di.openProgram(currentProgram);
        Listing lst = currentProgram.getListing();
        ReferenceManager rm = currentProgram.getReferenceManager();

        println("===== MATCHED STRINGS + XREFS =====");
        DataIterator dit = lst.getDefinedData(true);
        while (dit.hasNext() && !monitor.isCancelled()) {
            Data d = dit.next();
            if (d == null || !d.hasStringValue()) continue;
            Object v = d.getValue();
            if (v == null) continue;
            String s = v.toString();
            String low = s.toLowerCase();
            boolean hit = false;
            for (String n : needles) { if (low.contains(n.toLowerCase())) { hit = true; break; } }
            if (!hit) continue;
            Address sa = d.getAddress();
            String disp = s.replace("\n", "\\n");
            if (disp.length() > 70) disp = disp.substring(0, 70);
            println("STR @" + sa + " : \"" + disp + "\"");
            ReferenceIterator ri = rm.getReferencesTo(sa);
            boolean any = false;
            while (ri.hasNext()) {
                any = true;
                Reference ref = ri.next();
                Address from = ref.getFromAddress();
                Function f = getFunctionContaining(from);
                if (f != null) {
                    println("   xref @" + from + "  in FUNC " + f.getName() + " @" + f.getEntryPoint());
                    funcs.add(f.getEntryPoint().getOffset());
                } else {
                    // no function: show the surrounding code block and its nearest symbol
                    Symbol ps = getSymbolBefore(from);
                    println("   xref @" + from + "  (NO FUNC; nearest sym: "
                        + (ps != null ? ps.getName() + " @" + ps.getAddress() : "none") + ")");
                }
            }
            if (!any) println("   (no xrefs)");
        }

        for (long k : known) funcs.add(k);

        println("\n===== DECOMPILES (" + funcs.size() + " funcs) =====");
        for (Long off : funcs) {
            Address a = toAddr(off);
            Function f = getFunctionAt(a);
            if (f == null) f = getFunctionContaining(a);
            if (f == null) { println("== NO FUNC @ 0x" + Long.toHexString(off)); continue; }
            println("\n==== " + f.getName() + " @ " + f.getEntryPoint() + " ====");
            println(decomp(f));
        }
        di.dispose();
    }
}
